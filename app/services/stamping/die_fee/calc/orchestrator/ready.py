"""模具费计算就绪统计。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.stamping_die_fee_vo import StampingDieFeeCalcReadyVO
from app.services.stamping.die_fee.calc.orchestrator.deps import DieFeeCalcDeps
from app.services.stamping.die_fee.calc.orchestrator.identity import (
    matches_part,
    parts_for_identity,
    strip_optional,
)
from app.services.stamping.die_fee.calc.weight_resolver import PreviousWeightIndex
from app.services.stamping.die_fee.fee_math import ZERO


def collect_calc_ready(
    db: Session,
    deps: DieFeeCalcDeps,
    *,
    year: int,
    location: str | None = None,
    vehicle_model: str | None = None,
    stamping_supplier: str | None = None,
    version: str | None = None,
) -> StampingDieFeeCalcReadyVO:
    supplier_filter = strip_optional(stamping_supplier)
    version_filter = strip_optional(version)
    has_unit_price = False
    calculable_count = 0
    part_count = 0
    if location and vehicle_model:
        all_parts = deps.die_repo.list_with_processes(
            db, location=location, vehicle_model=vehicle_model
        )
        persist_parts = parts_for_identity(
            all_parts,
            stamping_supplier=supplier_filter,
            version=version_filter,
        )
        part_count = len(persist_parts)
        price = deps.unit_price_repo.get_effective(
            db, location=location, vehicle_model=vehicle_model
        )
        has_unit_price = (
            price is not None and price.allocation_qty is not None and price.allocation_qty > ZERO
        )
        previous_weights = PreviousWeightIndex()
        if has_unit_price and price is not None:
            for part in all_parts:
                calculated, previous_weights = deps.part_calculator.calc_part(
                    part,
                    steel_plate_unit_price=price.steel_plate_unit_price,
                    progressive_die_unit_price=price.progressive_die_unit_price,
                    allocation_qty=price.allocation_qty,
                    previous_weights=previous_weights,
                )
                if calculated is not None and matches_part(
                    part,
                    stamping_supplier=supplier_filter,
                    version=version_filter,
                ):
                    calculable_count += 1
    return StampingDieFeeCalcReadyVO(
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        stamping_supplier=supplier_filter,
        version=version_filter,
        part_count=part_count,
        calculable_count=calculable_count,
        has_unit_price=has_unit_price,
    )
