"""整本回滚：只删本通道头 / 切点 / 链接。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import quoted
from app.common.period import format_period
from app.exceptions.base import BusinessException, NotFoundException
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
from app.services.engineering_change.material_change.codes import (
    ECM_PENDING_VERSION,
    ECM_ROLLBACK_BLOCKED,
    ecm_sheet,
)
from app.services.stamping.part.service import StampingPartService

_log_repo = MaterialChangeUploadLogRepository()
_order_repo = MaterialChangeOrderRepository()
_link_repo = MaterialChangeEffectLinkRepository()


class MaterialChangeRollbackService:
    def rollback(self, db: Session, upload_log_id: int, current_user: UserVO) -> None:
        _ = current_user
        log_row = _log_repo.get_by_id(db, upload_log_id)
        if log_row is None:
            raise NotFoundException("材料变更记录不存在")
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
        if log_row.status == "success":
            for order in orders:
                if _order_repo.has_later_success(
                    db,
                    location=order.location,
                    stamping_supplier=order.stamping_supplier,
                    vehicle_model=order.vehicle_model,
                    part_number=order.part_number,
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
                StampingPartService().get_by_id(db, order.source_part_id)
        links = _link_repo.list_by_upload_log_id(db, upload_log_id)
        for link in links:
            _link_repo.delete(db, link)
        copies = [order for order in orders if order.copied_from_order_id is not None]
        originals = [order for order in orders if order.copied_from_order_id is None]
        for order in copies:
            _order_repo.delete(db, order)
        for order in originals:
            _order_repo.delete(db, order)
        _log_repo.delete(db, log_row)
        db.commit()
