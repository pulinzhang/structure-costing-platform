"""核算结果 → 落库载荷。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.common.audit import AUDIT_PENDING
from app.common.swing_shear import applied_swing_shear_fee_per_ton
from app.models.stamping import StampingPart
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostCalcAmounts,
    StampingPartCostPartSnapshot,
    StampingPartCostUpsertPayload,
)
from app.services.costing.stamping_part_cost.calc.constants import FORMULA_VERSION


def build_part_cost_upsert(
    *,
    year: int,
    month: int,
    location: str,
    supplier: str,
    part: StampingPart,
    snapshot: StampingPartCostPartSnapshot,
    density: Decimal,
    loss_rate: Decimal,
    recovery_rate: Decimal,
    amounts: StampingPartCostCalcAmounts | None,
    swing_shear_fee_per_ton: Decimal,
    calc_batch_id: str | None,
    calculated_at: datetime,
    calc_status: str,
    calc_fail_reason: str | None,
    created_by: str | None,
    updated_by: str | None,
) -> StampingPartCostUpsertPayload:
    payload = StampingPartCostUpsertPayload(
        year=year,
        month=month,
        location=location,
        stamping_supplier=supplier,
        vehicle_model=part.vehicle_model,
        version=part.version,
        snapshot=snapshot,
        density=density,
        material_loss_rate=loss_rate,
        scrap_recovery_rate=recovery_rate,
        calc_status=calc_status,
        audit_status=AUDIT_PENDING,
        updated_by=updated_by,
        created_by=created_by,
        calc_batch_id=calc_batch_id,
        calc_fail_reason=calc_fail_reason,
        formula_version=FORMULA_VERSION,
        calculated_at=calculated_at,
    )
    if amounts is None:
        payload.swing_shear_fee_per_ton = applied_swing_shear_fee_per_ton(
            has_swing_shear=snapshot.has_swing_shear,
            fee_per_ton=swing_shear_fee_per_ton,
        )
        return payload
    payload.density = amounts.density
    payload.material_loss_rate = amounts.material_loss_rate
    payload.scrap_recovery_rate = amounts.scrap_recovery_rate
    payload.blank_weight_kg = amounts.blank_weight_kg
    payload.finished_total_kg = amounts.finished_total_kg
    payload.scrap_weight_kg = amounts.scrap_weight_kg
    payload.material_utilization_pct = amounts.material_utilization_pct
    payload.steel_price_id = amounts.steel_price_id
    payload.steel_mill = amounts.steel_mill
    payload.steel_ton_price = amounts.steel_ton_price
    payload.swing_shear_fee_per_ton = amounts.swing_shear_fee_per_ton
    payload.scrap_price_id = amounts.scrap_price_id
    payload.scrap_ton_price = amounts.scrap_ton_price
    payload.process_fee_id = amounts.process_fee_id
    payload.process_fee_amount = amounts.process_fee_amount
    payload.die_fee_id = amounts.die_fee_id
    payload.die_fee_amount = amounts.die_fee_amount
    payload.gauge_fee_id = amounts.gauge_fee_id
    payload.gauge_fee_amount = amounts.gauge_fee_amount
    payload.material_amount_sheet = amounts.material_amount_sheet
    payload.loss_scrap_deduction = amounts.loss_scrap_deduction
    payload.process_scrap_deduction = amounts.process_scrap_deduction
    payload.scrap_amount_sheet = amounts.scrap_amount_sheet
    payload.material_net_per_part = amounts.material_net_per_part
    payload.direct_cost = amounts.direct_cost
    payload.finished_finance_fee = amounts.finished_finance_fee
    payload.finished_management_fee = amounts.finished_management_fee
    payload.finished_warehouse_packaging_fee = amounts.finished_warehouse_packaging_fee
    payload.finished_pretax_profit_fee = amounts.finished_pretax_profit_fee
    payload.unit_cost = amounts.unit_cost
    return payload
