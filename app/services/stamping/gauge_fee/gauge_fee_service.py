"""冲压检具费查询、单条改删、整包删除。"""

import logging

from sqlalchemy.orm import Session

from app.common.audit import audit_update
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.stamping.gauge_fee_repository import StampingGaugeFeeRepository
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
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

logger = logging.getLogger("service.stamping_gauge_fee")


class StampingGaugeFeeService:
    def __init__(self) -> None:
        self.repository = StampingGaugeFeeRepository()
        self.stamping_part_repo = StampingPartRepository()

    def list_scope_filters(self, db: Session, location: str | None) -> StampingGaugeFeeFilterVO:
        raw = self.stamping_part_repo.get_cascade_filter_options(
            db,
            location=(location or "").strip() or None,
            stamping_supplier=None,
            vehicle_model=None,
        )
        return StampingGaugeFeeFilterVO(
            locations=list(raw["locations"]),
            vehicle_models=list(raw["vehicle_models"]),
        )

    def paginate(
        self, db: Session, query: StampingGaugeFeeQuery
    ) -> tuple[list[StampingGaugeFeeVO], int, StampingGaugeFeeListFiltersVO]:
        location = (query.location or "").strip() or None
        vehicle = normalize_vehicle_model(query.vehicle_model) if query.vehicle_model else None
        part_number = (query.part_number or "").strip() or None
        skip = (query.page - 1) * query.size
        summary = self.repository.summarize_by_filters(
            db,
            location=location,
            vehicle_model=vehicle,
            part_number=part_number,
            status=query.status,
        )
        rows = self.repository.list_page(
            db,
            location=location,
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
