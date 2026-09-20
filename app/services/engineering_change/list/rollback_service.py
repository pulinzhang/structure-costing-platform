"""
删除本次变更 = 回滚业务对象，再物理删除本本三张表。

为何逆序：先删后写的依赖（采购对象/拆解挂在新树上），再清工艺/布点，最后删新树并恢复旧 L0 失效月。
其后还有未回滚变更、或对象已审未反审 → 拒收，避免半截时间轴。
列表删任意一条变更单，都按 upload_log_id 整本回滚并删除，不留 rolled_back 行。
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.engineering_change_gates import (
    EC_ROLLBACK_BLOCKED,
    EC_ROLLBACK_REFERENCED,
    EFFECT_ANNUAL_PART_PRICE,
    EFFECT_ASSEMBLY_L0,
    EFFECT_DIE_FEE,
    EFFECT_DIE_PART,
    EFFECT_GAUGE_FEE,
    EFFECT_PACKAGING_FEE,
    EFFECT_PROCESS_PART,
    EFFECT_PROCUREMENT_LIST,
    EFFECT_PROCUREMENT_OBJECT,
    EFFECT_WELDING_BREAKDOWN,
)
from app.exceptions.base import BusinessException, NotFoundException
from app.models.engineering_change.effect_link import EngineeringChangeEffectLink
from app.repositories.engineering_change.change_order_repository import (
    EngineeringChangeOrderRepository,
)
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkRepository,
)
from app.repositories.engineering_change.upload_log_repository import (
    EngineeringChangeUploadLogRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.annual_part_price.service import BomAnnualPartPriceService
from app.services.bom.bom_service import BomService
from app.services.bom.packaging_transport_fee.service import BomPackagingTransportFeeService
from app.services.bom.procurement_object.service import BomProcurementObjectService
from app.services.bom.welding_process_breakdown.service import BomWeldingProcessBreakdownService
from app.services.stamping.die.die_service import StampingDieService
from app.services.stamping.die_fee.die_fee_service import StampingDieFeeService
from app.services.stamping.gauge_fee.gauge_fee_service import StampingGaugeFeeService
from app.services.stamping.stamping_service import StampingPartService

logger = logging.getLogger("service.engineering_change.rollback")


class EngineeringChangeRollbackService:
    def __init__(self) -> None:
        self.log_repo = EngineeringChangeUploadLogRepository()
        self.change_order_repo = EngineeringChangeOrderRepository()
        self.link_repo = EngineeringChangeEffectLinkRepository()
        self.bom_service = BomService()
        self.po_service = BomProcurementObjectService()
        self.breakdown_service = BomWeldingProcessBreakdownService()
        self.stamping_service = StampingPartService()
        self.die_service = StampingDieService()
        self.gauge_fee_service = StampingGaugeFeeService()
        self.die_fee_service = StampingDieFeeService()
        self.packaging_fee_service = BomPackagingTransportFeeService()
        self.annual_part_price_service = BomAnnualPartPriceService()

    def rollback(self, db: Session, upload_log_id: int, current_user: UserVO) -> None:
        log_row = self.log_repo.get_by_id(db, upload_log_id)
        if log_row is None:
            raise NotFoundException("工程变更记录不存在")
        if log_row.status == "pending":
            raise BusinessException(EC_ROLLBACK_BLOCKED, code=409)
        change_orders = self.change_order_repo.list_by_upload_log_id(db, upload_log_id)
        if log_row.status == "success":
            if not change_orders or any(
                change_order.status != "active" for change_order in change_orders
            ):
                raise BusinessException(EC_ROLLBACK_BLOCKED, code=409)
            for change_order in change_orders:
                if not change_order.after_assembly_part_number:
                    continue
                later = self.change_order_repo.list_later_success_using_after_as_before(
                    db,
                    location=log_row.location,
                    vehicle_model=log_row.vehicle_model,
                    after_assembly_part_number=change_order.after_assembly_part_number,
                    after_upload_log_id=log_row.id,
                )
                if later:
                    raise BusinessException(EC_ROLLBACK_BLOCKED, code=409)

        links = self.link_repo.list_by_upload_log_id_desc(db, upload_log_id)
        try:
            if log_row.status == "success":
                for link in links:
                    self._rollback_link(db, link, current_user=current_user)
            self.link_repo.delete_by_upload_log_id(db, upload_log_id)
            self.change_order_repo.delete_by_upload_log_id(db, upload_log_id)
            self.log_repo.delete(db, log_row)
            db.commit()
        except BusinessException:
            db.rollback()
            raise
        except IntegrityError:
            db.rollback()
            # 加工费/模具费/焊接费等对零件、布点、拆解 RESTRICT；转业务异常给前端 Toast，勿 500
            raise BusinessException(EC_ROLLBACK_REFERENCED, code=409) from None
        except Exception:
            db.rollback()
            logger.exception("工程变更回滚失败 upload_log_id=%s", upload_log_id)
            raise

    def _rollback_link(
        self,
        db: Session,
        link: EngineeringChangeEffectLink,
        *,
        current_user: UserVO,
    ) -> None:
        kind = link.effect_kind
        if kind == EFFECT_DIE_FEE and link.after_id:
            self.die_fee_service.delete_for_engineering_change_rollback(db, link.after_id)
            return
        if kind == EFFECT_PACKAGING_FEE and link.after_id:
            self.packaging_fee_service.delete_for_engineering_change_rollback(db, link.after_id)
            return
        if kind == EFFECT_ANNUAL_PART_PRICE and link.after_id:
            self.annual_part_price_service.delete_for_engineering_change_rollback(db, link.after_id)
            return
        if kind == EFFECT_GAUGE_FEE and link.after_id:
            self.gauge_fee_service.delete_for_engineering_change_rollback(db, link.after_id)
            return
        if kind == EFFECT_PROCUREMENT_OBJECT and link.after_id:
            self.po_service.delete_object_for_engineering_change_rollback(db, link.after_id)
            return
        if kind == EFFECT_PROCUREMENT_LIST and link.after_id:
            self.po_service.delete_list_if_empty_for_engineering_change_rollback(db, link.after_id)
            return
        if kind == EFFECT_WELDING_BREAKDOWN and link.after_id:
            self.breakdown_service.delete_node_for_engineering_change_rollback(db, link.after_id)
            return
        if kind == EFFECT_ASSEMBLY_L0:
            if link.after_id:
                self.bom_service.delete_engineering_change_tree(
                    db, root_id=link.after_id, current_user=current_user
                )
            if link.before_id:
                self.bom_service.clear_l0_expiry(
                    db, root_id=link.before_id, current_user=current_user
                )
            return
        if kind == EFFECT_PROCESS_PART:
            self.stamping_service.rollback_engineering_change_part(
                db,
                after_part_id=link.after_id,
                before_part_id=link.before_id,
                current_user=current_user,
            )
            return
        if kind == EFFECT_DIE_PART:
            self.die_service.rollback_engineering_change_part(
                db,
                after_part_id=link.after_id,
                before_part_id=link.before_id,
                current_user=current_user,
            )
            return
        logger.info("回滚未识别 effect_kind=%s id=%s", kind, link.id)
        raise BusinessException(f"回滚未识别效果类型: {kind}")
