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
    EFFECT_ANNUAL_PART_PRICE,
    EFFECT_ASSEMBLY_L0,
    EFFECT_DIE_FEE,
    EFFECT_DIE_PART,
    EFFECT_GAUGE_FEE,
    EFFECT_PACKAGING_FEE,
    EFFECT_PART_MATERIAL_CHANGE,
    EFFECT_PROCESS_PART,
    EFFECT_PROCUREMENT_LIST,
    EFFECT_PROCUREMENT_OBJECT,
    EFFECT_WELDING_BREAKDOWN,
)
from app.exceptions.base import BusinessException, NotFoundException
from app.models.engineering_change.design_change.effect_link import EngineeringChangeEffectLink
from app.repositories.engineering_change.design_change.change_order_repository import (
    EngineeringChangeOrderRepository,
)
from app.repositories.engineering_change.design_change.effect_link_repository import (
    EngineeringChangeEffectLinkRepository,
)
from app.repositories.engineering_change.design_change.upload_log_repository import (
    EngineeringChangeUploadLogRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.annual_part_price.service import BomAnnualPartPriceService
from app.services.bom.bom.engineering import BomEngineeringService
from app.services.bom.packaging_transport_fee.service import BomPackagingTransportFeeService
from app.services.bom.procurement_object.service import BomProcurementObjectService
from app.services.bom.welding_process_breakdown.service import BomWeldingProcessBreakdownService
from app.services.settings.foreign_key.service import STILL_REFERENCED, ensure_deletable
from app.services.stamping.die.engineering.service import StampingDieEngineeringService
from app.services.stamping.die_fee.service import StampingDieFeeService
from app.services.stamping.gauge_fee.service import StampingGaugeFeeService
from app.services.stamping.part.engineering.design_change.service import StampingDesignChangeService
from app.services.stamping.part.engineering.material_change import StampingMaterialChangeService

logger = logging.getLogger("service.engineering_change.rollback")


class EngineeringChangeRollbackService:
    def __init__(self) -> None:
        self.log_repo = EngineeringChangeUploadLogRepository()
        self.change_order_repo = EngineeringChangeOrderRepository()
        self.link_repo = EngineeringChangeEffectLinkRepository()
        self.bom_service = BomEngineeringService()
        self.po_service = BomProcurementObjectService()
        self.breakdown_service = BomWeldingProcessBreakdownService()
        self.stamping_service = StampingDesignChangeService()
        self.material_service = StampingMaterialChangeService()
        self.die_service = StampingDieEngineeringService()
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
        location = log_row.location
        vehicle_model = log_row.vehicle_model
        try:
            if log_row.status == "success":
                for link in links:
                    self._rollback_link(db, link, current_user=current_user)
            link_ids = [link.id for link in links]
            if link_ids:
                ensure_deletable(
                    db,
                    "engineering_change_effect_links",
                    [{"id": link_id} for link_id in link_ids],
                    subject="这些设计变更效果",
                )
            self.link_repo.delete_by_upload_log_id(db, upload_log_id)
            order_ids = [change_order.id for change_order in change_orders]
            if order_ids:
                ensure_deletable(
                    db,
                    "engineering_change_orders",
                    [{"id": order_id} for order_id in order_ids],
                    subject="这些设计变更单",
                )
            self.change_order_repo.delete_by_upload_log_id(db, upload_log_id)
            ensure_deletable(
                db,
                "engineering_change_upload_logs",
                [{"id": log_row.id}],
                subject=f"设计变更「{location} {vehicle_model}」",
            )
            self.log_repo.delete(db, log_row)
            db.commit()
        except BusinessException:
            db.rollback()
            raise
        except IntegrityError:
            db.rollback()
            raise BusinessException(STILL_REFERENCED) from None
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
        if kind == EFFECT_PART_MATERIAL_CHANGE and link.after_id:
            self.material_service.delete(db, [link.after_id])
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
        raise BusinessException(f"撤销时遇到不认识的记录（{kind}），请联系管理员。")
