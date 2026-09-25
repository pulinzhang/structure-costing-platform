"""
整本回滚：先按链接让冲压删历史，再删本通道链接、切点单、头。

历史只在导入成功时写入。after_id 是冲压材料变更历史主键，没有外键，
必须趁链接还在时按 id 删。链接、切点单的外键 RESTRICT 指回头，所以后删。
同一零件更晚还有材料变更则整本拒收，避免时间轴留洞。
冲压 delete 会查钢材联动价的逻辑引用；挡住则抛「仍被引用」，这里不 commit。
零件主表和工艺上的材料列不动。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import quoted
from app.common.period import format_period
from app.exceptions.base import BusinessException, NotFoundException
from app.parsers.engineering_change.material_change.codes import (
    ECM_PENDING_VERSION,
    ECM_ROLLBACK_BLOCKED,
    ecm_sheet,
)
from app.repositories.engineering_change.material_change.effect_link_repository import (
    MaterialChangeEffectLinkRepository,
)
from app.repositories.engineering_change.material_change.order_repository import (
    MaterialChangeOrderRepository,
)
from app.repositories.engineering_change.material_change.upload_log_repository import (
    MaterialChangeUploadLogRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.part.engineering.material_change import StampingMaterialChangeService

_log_repo = MaterialChangeUploadLogRepository()
_order_repo = MaterialChangeOrderRepository()
_link_repo = MaterialChangeEffectLinkRepository()


class MaterialChangeRollbackService:
    def rollback(self, db: Session, upload_log_id: int, current_user: UserVO) -> None:
        _ = current_user
        log_row = _log_repo.get_by_id(db, upload_log_id)
        if log_row is None:
            raise NotFoundException("材料变更记录不存在")
        # 导入还在跑，历史和链接都可能写到一半。
        if log_row.status == "pending":
            raise BusinessException(
                ecm_sheet(
                    ECM_PENDING_VERSION,
                    f"{format_period(log_row.effective_year, log_row.effective_month)} 还在导入。"
                    "请等它结束再删。",
                ),
                code=409,
            )
        orders = _order_repo.list_by_upload_log_id(db, upload_log_id)
        materials = StampingMaterialChangeService()
        # 成功本才有历史。先确认没有更晚的一刀，这一步只查不删。
        if log_row.status == "success":
            for order in orders:
                if materials.has_later(
                    db,
                    part_id=order.source_part_id,
                    effective_year=order.effective_year,
                    effective_month=order.effective_month,
                ):
                    raise BusinessException(
                        ecm_sheet(
                            ECM_ROLLBACK_BLOCKED,
                            f"零件{quoted(order.part_number)}在"
                            f"{format_period(order.effective_year, order.effective_month)}之后还有材料变更。"
                            "请先删掉更晚的那本。",
                        ),
                        code=409,
                    )
        links = _link_repo.list_by_upload_log_id(db, upload_log_id)
        # after_id 可空：只删上传时实际写下的历史行。delete 只 flush，引用检查在冲压侧。
        if log_row.status == "success":
            for link in links:
                if link.after_id is not None:
                    materials.delete(db, [link.after_id])
        # 子表先于父表：链接 → 切点单 → 上传头。任一步失败，已 flush 的删除随请求回滚。
        for link in links:
            _link_repo.delete(db, link)
        for order in orders:
            _order_repo.delete(db, order)
        _log_repo.delete(db, log_row)
        db.commit()
