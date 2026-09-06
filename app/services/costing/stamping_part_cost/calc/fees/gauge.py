"""检具费：档案存万元与万台，核价时万元÷万台 = 元/件；缺档或分摊≤0 记 0。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.stamping.gauge_fee_repository import StampingGaugeFeeRepository
from app.services.costing.stamping_part_cost.calc.constants import (
    AMOUNT_QUANTIZE,
    quantize,
)
from app.services.costing.stamping_part_cost.calc.fees.match import location_and_vehicle_keys
from app.services.costing.stamping_part_cost.helpers import location_candidates

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class GaugeFeeLookup:
    gauge_fee_id: int | None
    gauge_fee_amount: Decimal


def gauge_fee_yuan_per_part(gauge_fee_wan: Decimal, allocation_qty_wan: Decimal) -> Decimal:
    """档案存万元、万台；万元÷万台 = 元/件。分摊数量 ≤ 0 时记 0。"""
    if allocation_qty_wan <= ZERO:
        return ZERO
    return quantize(gauge_fee_wan / allocation_qty_wan, AMOUNT_QUANTIZE)


class GaugeFeeResolver:
    """只负责检具费。与模具费公式无关：模具费上游已是元/件，检具费本层才摊。"""

    def __init__(self, gauge_fee_repo: StampingGaugeFeeRepository | None = None) -> None:
        self.gauge_fee_repo = gauge_fee_repo or StampingGaugeFeeRepository()

    def count_for_ready(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str | None,
    ) -> int:
        best = 0
        for candidate in location_candidates(location):
            count = self.gauge_fee_repo.count_effective(
                db,
                location=candidate,
                vehicle_model=vehicle_model,
            )
            if count > best:
                best = count
        return best

    def lookup(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_number: str,
    ) -> GaugeFeeLookup:
        for loc, vehicle in location_and_vehicle_keys(
            location=location, vehicle_model=vehicle_model
        ):
            row = self.gauge_fee_repo.get_effective_by_part(
                db,
                location=loc,
                vehicle_model=vehicle,
                part_number=part_number,
            )
            if row is None:
                continue
            return GaugeFeeLookup(
                gauge_fee_id=row.id,
                gauge_fee_amount=gauge_fee_yuan_per_part(
                    Decimal(str(row.gauge_fee)),
                    Decimal(str(row.allocation_qty)),
                ),
            )
        return GaugeFeeLookup(gauge_fee_id=None, gauge_fee_amount=ZERO)
