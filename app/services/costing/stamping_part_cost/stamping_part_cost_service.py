"""
冲压零件价格核算服务（CRUD / 审核门面）

计算逻辑见 app.services.costing.stamping_part_cost.calc。
"""

from __future__ import annotations

from typing import Any


from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, audit_update, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.costing import StampingPartCostCalcLog
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostBatchApproveDTO,
    StampingPartCostBatchReverseAuditDTO,
    StampingPartCostCalcDTO,
    StampingPartCostDeleteDTO,
    StampingPartCostManualUnitCostDTO,
    StampingPartCostQuery,
)
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostBatchAuditResultVO,
    StampingPartCostBatchDeleteResultVO,
    StampingPartCostCalcLogVO,
    StampingPartCostCalcReadyVO,
    StampingPartCostCalcResultVO,
    StampingPartCostVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.stamping_part_cost.calc.constants import (
    AMOUNT_QUANTIZE,
    DUPLICATE_SCOPE_CALC_MESSAGE,
    STATUS_FAILED,
)
from app.services.costing.stamping_part_cost.calc.models import (
    DuplicateScopeCalcError,
    ProgressCallback,
)
from app.services.costing.stamping_part_cost.calc.orchestrator import (
    StampingPartCostCalcOrchestrator,
)
from app.services.costing.stamping_part_cost.calc.scope import require_scope

# 兼容旧导入路径
__all__ = [
    "DUPLICATE_SCOPE_CALC_MESSAGE",
    "DuplicateScopeCalcError",
    "StampingPartCostService",
]


class StampingPartCostService:
    """冲压零件价格核算：列表/审核 + 计算委托编排器。"""

    def __init__(self) -> None:
        self.cost_repo = StampingPartCostRepository()
        self.steel_repo = SteelPriceRepository()
        self.orchestrator = StampingPartCostCalcOrchestrator()

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        month: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> StampingPartCostCalcReadyVO:
        return self.orchestrator.get_calc_ready(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )

    def begin_processing(
        self,
        db: Session,
        dto: StampingPartCostCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingPartCostCalcLog:
        return self.orchestrator.begin_processing(
            db,
            dto,
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        self.orchestrator.mark_log_failed(
            db, log_id=log_id, detail_text=detail_text
        )

    def calculate(
        self,
        db: Session,
        dto: StampingPartCostCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> StampingPartCostCalcResultVO:
        return self.orchestrator.calculate(
            db,
            dto,
            current_user,
            progress_callback=progress_callback,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
        )

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingPartCostCalcLogVO], int]:
        return self.orchestrator.calc_log_service.list_calc_logs(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            page=page,
            size=size,
        )

    def get_calc_log(
        self, db: Session, log_id: int
    ) -> StampingPartCostCalcLogVO | None:
        return self.orchestrator.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> bool:
        return self.orchestrator.calc_log_service.delete_calc_log(db, log_id)

    def paginate(
        self, db: Session, query: StampingPartCostQuery
    ) -> tuple[list[StampingPartCostVO], int, dict[str, Any]]:
        skip = (query.page - 1) * query.size
        rows, total = self.cost_repo.paginate(
            db,
            year=query.year,
            month=query.month,
            location=query.location,
            stamping_supplier=query.stamping_supplier,
            vehicle_model=query.vehicle_model,
            version=query.version,
            part_number=query.part_number,
            audit_status=query.audit_status,
            skip=skip,
            limit=query.size,
        )
        filters = {
            "years": self.cost_repo.get_distinct_years(db),
            "months": self.cost_repo.get_distinct_months(db, year=query.year),
            "locations": self.cost_repo.get_distinct_locations(
                db, year=query.year, month=query.month
            ),
            "suppliers": self.cost_repo.get_distinct_suppliers(
                db,
                year=query.year,
                month=query.month,
                location=query.location,
            ),
            "summary": self.cost_repo.summarize_by_filters(
                db,
                year=query.year,
                month=query.month,
                location=query.location,
                stamping_supplier=query.stamping_supplier,
                vehicle_model=query.vehicle_model,
                version=query.version,
                part_number=query.part_number,
                audit_status=query.audit_status,
            ),
        }
        return (
            [StampingPartCostVO.model_validate(r) for r in rows],
            total,
            filters,
        )

    def get_by_id(self, db: Session, cost_id: int) -> StampingPartCostVO | None:
        record = self.cost_repo.get_by_id(db, cost_id)
        if record is None:
            return None
        return StampingPartCostVO.model_validate(record)

    def update_manual_unit_cost(
        self,
        db: Session,
        cost_id: int,
        dto: StampingPartCostManualUnitCostDTO,
        current_user: UserVO,
    ) -> StampingPartCostVO:
        """仅允许对计算失败且未审核的记录手工录入最终单件成本。"""
        record = self.cost_repo.get_by_id(db, cost_id)
        if not record:
            raise BusinessException(f"核算记录不存在: id={cost_id}")
        if record.calc_status != STATUS_FAILED:
            raise BusinessException("仅计算失败的记录允许手工改价")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再改价")

        remark = (dto.remark or "").strip()
        if not remark:
            raise BusinessException("备注不能为空")

        unit_cost = Decimal(str(dto.unit_cost)).quantize(
            AMOUNT_QUANTIZE, rounding=ROUND_HALF_UP
        )
        updated = self.cost_repo.update_fields(
            db,
            cost_id,
            {
                "unit_cost": unit_cost,
                "remark": remark,
                **audit_update(current_user),
            },
        )
        if not updated:
            raise BusinessException(f"核算记录不存在: id={cost_id}")
        return StampingPartCostVO.model_validate(updated)

    def list_years(self, db: Session) -> list[int]:
        years = set(self.cost_repo.get_distinct_years(db))
        years.update(self.steel_repo.list_distinct_years(db))
        return sorted(years, reverse=True)

    def list_locations(self, db: Session, year: int | None = None) -> list[str]:
        return self.cost_repo.get_distinct_locations(db, year=year)

    def list_suppliers(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
    ) -> list[str]:
        return self.cost_repo.get_distinct_suppliers(
            db, year=year, month=month, location=location
        )

    def batch_delete(
        self, db: Session, dto: StampingPartCostDeleteDTO
    ) -> StampingPartCostBatchDeleteResultVO:
        location, supplier = require_scope(dto)
        skipped = self.cost_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            statuses=[AUDIT_APPROVED],
        )
        deleted = self.cost_repo.delete_unaudited_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )
        db.commit()
        return StampingPartCostBatchDeleteResultVO(
            deleted_count=deleted,
            skipped_approved_count=skipped,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )

    def batch_approve(
        self,
        db: Session,
        dto: StampingPartCostBatchApproveDTO,
        current_user: UserVO,
    ) -> StampingPartCostBatchAuditResultVO:
        location, supplier = require_scope(dto)
        updated = self.cost_repo.approve_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            audited_by=display_name(current_user),
            audited_at=now(),
            audit_remark=dto.audit_remark,
            updated_by=display_name(current_user),
        )
        skipped = self.cost_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            statuses=[AUDIT_APPROVED],
        ) - updated
        db.commit()
        return StampingPartCostBatchAuditResultVO(
            updated_count=updated,
            skipped_count=max(skipped, 0),
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: StampingPartCostBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> StampingPartCostBatchAuditResultVO:
        location, supplier = require_scope(dto)
        updated = self.cost_repo.reverse_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            reverse_audited_by=display_name(current_user),
            reverse_audited_at=now(),
            reverse_audit_remark=dto.reverse_audit_remark,
            updated_by=display_name(current_user),
        )
        db.commit()
        return StampingPartCostBatchAuditResultVO(
            updated_count=updated,
            skipped_count=0,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )
