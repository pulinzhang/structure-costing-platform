"""冲压检具费查询、单条改删、整包删除；工程变更入口转发。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import audit_update
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.stamping.gauge_fee.repository import StampingGaugeFeeRepository
from app.schemas.dto.stamping_gauge_fee_dto import (
    StampingGaugeFeePatch,
    StampingGaugeFeeQuery,
    StampingGaugeFeeUpdate,
)
from app.schemas.vo.stamping_gauge_fee_vo import (
    StampingGaugeFeeFilterVO,
    StampingGaugeFeeListFiltersVO,
    StampingGaugeFeeListSummaryVO,
    StampingGaugeFeeScopeDeleteResultVO,
    StampingGaugeFeeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService
from app.services.stamping.gauge_fee.engineering.change import (
    EngineeringChangeGaugeFeeCloneResult,
)
from app.services.stamping.gauge_fee.engineering.change import (
    clone_revise_for_engineering_change as clone_revise_gauge_fee,
)
from app.services.stamping.gauge_fee.engineering.change import (
    delete_for_engineering_change_rollback as delete_gauge_fee_for_rollback,
)

logger = logging.getLogger("service.stamping_gauge_fee")


class StampingGaugeFeeService:
    def __init__(self) -> None:
        self.repository = StampingGaugeFeeRepository()

    def list_scope_filters(self, db: Session, location: str | None) -> StampingGaugeFeeFilterVO:
        location_service = LocationService()
        location_raw = (location or "").strip() or None
        return StampingGaugeFeeFilterVO(
            locations=location_service.list_enabled(db),
            vehicle_models=VehicleModelService().list_filter_codes(db, location_raw),
        )

    def paginate(
        self, db: Session, query: StampingGaugeFeeQuery
    ) -> tuple[list[StampingGaugeFeeVO], int, StampingGaugeFeeListFiltersVO]:
        location_raw = (query.location or "").strip() or None
        locations: list[str] | None = None
        if location_raw:
            locations = LocationService().expand_for_query(db, location_raw)
            if not locations:
                empty = StampingGaugeFeeListSummaryVO()
                return [], 0, StampingGaugeFeeListFiltersVO(summary=empty)
        vehicle = normalize_vehicle_model(query.vehicle_model) if query.vehicle_model else None
        part_number = (query.part_number or "").strip() or None
        skip = (query.page - 1) * query.size
        summary = self.repository.summarize_by_filters(
            db,
            locations=locations,
            vehicle_model=vehicle,
            part_number=part_number,
            status=query.status,
        )
        rows = self.repository.list_page(
            db,
            locations=locations,
            vehicle_model=vehicle,
            part_number=part_number,
            status=query.status,
            skip=skip,
            limit=query.size,
        )
        filters = StampingGaugeFeeListFiltersVO(
            summary=StampingGaugeFeeListSummaryVO.model_validate(summary),
        )
        return (
            [StampingGaugeFeeVO.model_validate(row) for row in rows],
            summary["total_count"],
            filters,
        )

    def update(
        self,
        db: Session,
        record_id: int,
        dto: StampingGaugeFeeUpdate,
        current_user: UserVO,
    ) -> StampingGaugeFeeVO:
        if not dto.model_fields_set:
            raise BusinessException("没有提供任何更新字段")
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException(f"检具费不存在: id={record_id}")
        audit = audit_update(current_user)
        patch: StampingGaugeFeePatch = {"updated_by": audit["updated_by"]}
        if "gauge_fee" in dto.model_fields_set:
            if dto.gauge_fee is None:
                raise BusinessException("检具费不能为空")
            patch["gauge_fee"] = dto.gauge_fee
        if "allocation_qty" in dto.model_fields_set:
            if dto.allocation_qty is None:
                raise BusinessException("项目分摊数量不能为空")
            patch["allocation_qty"] = dto.allocation_qty
        if "status" in dto.model_fields_set:
            if dto.status is None:
                raise BusinessException("状态不能为空")
            patch["status"] = dto.status
        try:
            record = self.repository.apply_patch(db, record, patch)
            db.commit()
            return StampingGaugeFeeVO.model_validate(record)
        except Exception:
            db.rollback()
            logger.exception("更新检具费失败: id=%s", record_id)
            raise

    def delete(self, db: Session, record_id: int) -> None:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException(f"检具费不存在: id={record_id}")
        try:
            self.repository.delete(db, record)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("删除检具费失败: id=%s", record_id)
            raise

    def delete_scope(
        self, db: Session, *, location: str, vehicle_model: str
    ) -> StampingGaugeFeeScopeDeleteResultVO:
        loc, vehicle = self._require_scope(location, vehicle_model)
        try:
            deleted = self.repository.delete_by_scope(db, location=loc, vehicle_model=vehicle)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return StampingGaugeFeeScopeDeleteResultVO(
            location=loc,
            vehicle_model=vehicle,
            deleted_count=deleted,
            message=f"已删除基地「{loc}」、项目「{vehicle}」检具费 {deleted} 条",
        )

    @staticmethod
    def _require_scope(location: str, vehicle_model: str) -> tuple[str, str]:
        loc = (location or "").strip()
        vehicle = normalize_vehicle_model(vehicle_model) or ""
        if not loc:
            raise BusinessException("请选择采购基地")
        if not vehicle:
            raise BusinessException("请选择项目")
        return loc, vehicle

    def clone_revise_for_engineering_change(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        old_part_number: str,
        new_part_number: str,
        current_user: UserVO,
    ) -> EngineeringChangeGaugeFeeCloneResult | None:
        """改图抄检具费。只 flush。实现见 engineering/change.py。"""
        return clone_revise_gauge_fee(
            self.repository,
            db,
            location=location,
            vehicle_model=vehicle_model,
            old_part_number=old_part_number,
            new_part_number=new_part_number,
            current_user=current_user,
        )

    def delete_for_engineering_change_rollback(self, db: Session, fee_id: int) -> None:
        """回滚删新检具费行。只 flush。"""
        delete_gauge_fee_for_rollback(self.repository, db, fee_id)
