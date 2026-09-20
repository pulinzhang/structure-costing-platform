"""模具费：取年度模具费最终价（已是元/件）。

零件价页只 lookup：缺档记 0，本层不补算、不挡算。
引擎补算见 costing-engine `annual_die_fee`（有布点且当年无结果才算）。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.services.costing.stamping_part_cost.calc.constants import (
    AMOUNT_QUANTIZE,
    quantize,
)
from app.services.costing.stamping_part_cost.calc.fees.match import location_and_vehicle_keys
from app.services.masterdata.location.location_service import LocationService

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class DieFeeLookup:
    die_fee_id: int | None
    die_fee_amount: Decimal


class DieFeeResolver:
    """只负责模具费。最终模具费已在上游按 万元÷万台 摊成元/件，本层不再除分摊。"""

    def __init__(self, die_fee_repo: StampingDieFeeRepository | None = None) -> None:
        self.die_fee_repo = die_fee_repo or StampingDieFeeRepository()

    def count_for_ready(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str | None,
    ) -> int:
        """基地别名下费用行合计（与 evaluate_die_fee_coverage 同口径：SUM，非 MAX）。"""
        total = 0
        names = LocationService().expand_for_query(db, location)
        for candidate in names:
            total += self.die_fee_repo.count_by_year_location(
                db,
                year=year,
                location=candidate,
                vehicle_model=vehicle_model,
            )
        return total

    def lookup(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        part_number: str,
    ) -> DieFeeLookup:
        names = LocationService().expand_for_query(db, location)
        for loc, vehicle in location_and_vehicle_keys(locations=names, vehicle_model=vehicle_model):
            row = self.die_fee_repo.get_by_year_location_vehicle_part(
                db,
                year=year,
                location=loc,
                vehicle_model=vehicle,
                part_number=part_number,
            )
            if row is None or row.final_die_fee is None:
                continue
            return DieFeeLookup(
                die_fee_id=row.id,
                die_fee_amount=quantize(Decimal(str(row.final_die_fee)), AMOUNT_QUANTIZE),
            )
        return DieFeeLookup(die_fee_id=None, die_fee_amount=ZERO)
