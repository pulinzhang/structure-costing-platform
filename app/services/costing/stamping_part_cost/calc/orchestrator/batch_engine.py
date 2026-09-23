"""批量核价引擎：逐件计算与落库载荷，不负责阶段文案与写库。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, audit_create, audit_update
from app.common.timezone import now
from app.models.stamping import StampingPart
from app.models.yishiyiyi import StampingScrapPrice
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostCalcAmounts,
    StampingPartCostCalcDTO,
    StampingPartCostUpsertPayload,
)
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostFailedItemVO
from app.schemas.vo.user_vo import UserVO
from app.services.costing.stamping_part_cost.calc.constants import (
    STATUS_FAILED,
    STATUS_SUCCESS,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.deps import PartCostCalcDeps
from app.services.costing.stamping_part_cost.calc.orchestrator.prep import CalcPrepContext
from app.services.costing.stamping_part_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.stamping_part_cost.calc.orchestrator.rates import PartCostCalcRates
from app.services.costing.stamping_part_cost.calc.orchestrator.upsert import (
    build_part_cost_upsert,
)
from app.services.costing.stamping_part_cost.calc.part_calculator import part_snapshot


class _SharedPartCostCall(TypedDict):
    part: StampingPart
    year: int
    month: int
    supplier: str
    scrap: StampingScrapPrice
    scrap_ton_price: Decimal
    density: Decimal
    loss_rate: Decimal
    recovery_rate: Decimal
    finance_rate: Decimal
    management_rate: Decimal
    warehouse_packaging_rate: Decimal
    pretax_profit_rate: Decimal
    swing_shear_fee_per_ton: Decimal


@dataclass(slots=True)
class BatchCalcOutcome:
    upsert_rows: list[StampingPartCostUpsertPayload] = field(default_factory=list)
    failed_items: list[StampingPartCostFailedItemVO] = field(default_factory=list)
    success_count: int = 0
    skipped_approved_count: int = 0


class BatchCalculationEngine:
    def __init__(self, deps: PartCostCalcDeps, rates: PartCostCalcRates) -> None:
        self._deps = deps
        self._rates = rates

    def run(
        self,
        db: Session,
        *,
        ctx: CalcPrepContext,
        dto: StampingPartCostCalcDTO,
        current_user: UserVO,
        calc_batch_id: str | None,
        progress: ProgressNotifier,
    ) -> BatchCalcOutcome:
        outcome = BatchCalcOutcome()
        audit = audit_create(current_user)
        update_audit = audit_update(current_user)
        calculated_at = now()
        total = len(ctx.parts)

        for index, part in enumerate(ctx.parts, start=1):
            self._process_part(
                db,
                part=part,
                dto=dto,
                ctx=ctx,
                calc_batch_id=calc_batch_id,
                calculated_at=calculated_at,
                existing_created_by=audit["created_by"],
                existing_updated_by=update_audit["updated_by"],
                new_updated_by=audit["updated_by"],
                outcome=outcome,
            )
            progress.tick_parts(index, total)

        return outcome

    @staticmethod
    def _part_supplier(part: StampingPart) -> str:
        return (part.stamping_supplier or "").strip()

    def _calc_part_cost(
        self,
        db: Session,
        *,
        part: StampingPart,
        year: int,
        month: int,
        scrap: StampingScrapPrice,
        scrap_ton_price: Decimal,
        material: str | None,
    ) -> StampingPartCostCalcAmounts | StampingPartCostFailedItemVO:
        rates = self._rates
        shared: _SharedPartCostCall = {
            "part": part,
            "year": year,
            "month": month,
            "supplier": self._part_supplier(part),
            "scrap": scrap,
            "scrap_ton_price": scrap_ton_price,
            "density": rates.density,
            "loss_rate": rates.loss_rate,
            "recovery_rate": rates.recovery_rate,
            "finance_rate": rates.finance_rate,
            "management_rate": rates.management_rate,
            "warehouse_packaging_rate": rates.warehouse_packaging_rate,
            "pretax_profit_rate": rates.pretax_profit_rate,
            "swing_shear_fee_per_ton": rates.swing_shear_fee_per_ton,
        }
        if part.is_tailor_welded:
            return self._deps.tailor_weld_calculator.calc_part_cost(db, **shared)
        return self._deps.part_calculator.calc_part_cost(db, **shared, material=material)

    def _process_part(
        self,
        db: Session,
        *,
        part: StampingPart,
        dto: StampingPartCostCalcDTO,
        ctx: CalcPrepContext,
        calc_batch_id: str | None,
        calculated_at: datetime,
        existing_created_by: str,
        existing_updated_by: str,
        new_updated_by: str,
        outcome: BatchCalcOutcome,
    ) -> None:
        deps = self._deps
        rates = self._rates
        existing = deps.cost_repo.get_by_business_key(
            db,
            year=dto.year,
            month=dto.month,
            location=part.location,
            stamping_supplier=self._part_supplier(part),
            vehicle_model=part.vehicle_model,
            version=part.version,
            part_number=part.part_number,
        )
        if existing is not None and existing.audit_status == AUDIT_APPROVED:
            outcome.skipped_approved_count += 1
            return

        resolved_material = None if part.is_tailor_welded else ctx.material_by_part_id.get(part.id)
        row_or_error = self._calc_part_cost(
            db,
            part=part,
            year=dto.year,
            month=dto.month,
            scrap=ctx.scrap,
            scrap_ton_price=ctx.scrap_ton_price,
            material=resolved_material,
        )
        created_by = None if existing else existing_created_by
        updated_by = existing_updated_by if existing else new_updated_by
        if isinstance(row_or_error, StampingPartCostFailedItemVO):
            outcome.failed_items.append(row_or_error)
            amounts = None
            calc_status = STATUS_FAILED
            fail_reason = row_or_error.reason
        else:
            outcome.success_count += 1
            amounts = row_or_error
            calc_status = STATUS_SUCCESS
            fail_reason = None
        snapshot = part_snapshot(part)
        if not part.is_tailor_welded and resolved_material is not None:
            snapshot.material = resolved_material
        outcome.upsert_rows.append(
            build_part_cost_upsert(
                year=dto.year,
                month=dto.month,
                location=part.location,
                supplier=self._part_supplier(part),
                part=part,
                snapshot=snapshot,  # 含是否利废 / 利用哪类废料，按本月落库
                density=rates.density,
                loss_rate=rates.loss_rate,
                recovery_rate=rates.recovery_rate,
                amounts=amounts,
                swing_shear_fee_per_ton=rates.swing_shear_fee_per_ton,
                calc_batch_id=calc_batch_id,
                calculated_at=calculated_at,
                calc_status=calc_status,
                calc_fail_reason=fail_reason,
                created_by=created_by,
                updated_by=updated_by,
            )
        )
