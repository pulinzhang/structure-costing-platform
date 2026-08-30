"""冲压零件核价：模具费 / 检具费取数（缺档记 0，不阻断计算）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.stamping.die_fee_repository import StampingDieFeeRepository
from app.repositories.stamping.gauge_fee_repository import StampingGaugeFeeRepository
from app.services.costing.stamping_part_cost.calc.constants import (
    AMOUNT_QUANTIZE,
    quantize,
)

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class ToolingFeeLookup:
    die_fee_id: int | None
    die_fee_amount: Decimal
    gauge_fee_id: int | None
    gauge_fee_amount: Decimal


def gauge_fee_yuan_per_part(gauge_fee_wan: Decimal, allocation_qty_wan: Decimal) -> Decimal:
    """档案存万元、万台；万元÷万台 = 元/件。分摊数量 ≤ 0 时记 0。"""
    if allocation_qty_wan <= ZERO:
        return ZERO
    return quantize(gauge_fee_wan / allocation_qty_wan, AMOUNT_QUANTIZE)


def lookup_tooling_fees(
    db: Session,
    *,
    year: int,
    location: str,
    vehicle_model: str,
    part_number: str,
    die_fee_repo: StampingDieFeeRepository | None = None,
    gauge_fee_repo: StampingGaugeFeeRepository | None = None,
) -> ToolingFeeLookup:
    die_repo = die_fee_repo or StampingDieFeeRepository()
    gauge_repo = gauge_fee_repo or StampingGaugeFeeRepository()

    die_row = die_repo.get_by_year_location_vehicle_part(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        part_number=part_number,
    )
    die_fee_id: int | None = None
    die_fee_amount = ZERO
    if die_row is not None and die_row.final_die_fee is not None:
        die_fee_id = die_row.id
        die_fee_amount = quantize(Decimal(str(die_row.final_die_fee)), AMOUNT_QUANTIZE)

    gauge_row = gauge_repo.get_effective_by_part(
        db,
        location=location,
        vehicle_model=vehicle_model,
        part_number=part_number,
    )
    gauge_fee_id: int | None = None
    gauge_fee_amount = ZERO
    if gauge_row is not None:
        gauge_fee_id = gauge_row.id
        gauge_fee_amount = gauge_fee_yuan_per_part(
            Decimal(str(gauge_row.gauge_fee)),
            Decimal(str(gauge_row.allocation_qty)),
        )

    return ToolingFeeLookup(
        die_fee_id=die_fee_id,
        die_fee_amount=die_fee_amount,
        gauge_fee_id=gauge_fee_id,
        gauge_fee_amount=gauge_fee_amount,
    )
