"""计算前置就绪：零件 / 钢材价 / 废料价 / 三类费用计数。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.stamping_part_cost_vo import StampingPartCostCalcReadyVO
from app.services.costing.stamping_part_cost.calc.orchestrator.deps import PartCostCalcDeps
from app.services.masterdata.location.location_service import LocationService
from app.services.stamping.process_fee.calc.orchestrator.ready import (
    evaluate_process_fee_coverage,
)


def collect_calc_ready(
    db: Session,
    deps: PartCostCalcDeps,
    *,
    year: int,
    month: int | None = None,
    location: str | None = None,
    vehicle_model: str | None = None,
    version: str | None = None,
) -> StampingPartCostCalcReadyVO:
    location_value = (location or "").strip() or None
    vehicle_value = (vehicle_model or "").strip() or None
    version_value = (version or "").strip() or None
    aliases = LocationService().expand_for_query(db, location_value) if location_value else []

    part_count = 0
    if location_value and vehicle_value:
        parts = deps.part_repo.list_with_processes(
            db,
            location=location_value,
            vehicle_model=vehicle_value,
            version=version_value,
        )
        part_count = len(parts)

    steel_price_count = 0
    scrap_price_count = 0
    process_fee_count = 0
    process_fee_complete = False
    die_fee_count = 0
    gauge_fee_count = 0

    if year and month and location_value:
        for candidate in aliases:
            count = deps.steel_repo.count_by_year_month_location(
                db, year=year, month=month, location=candidate
            )
            if count > steel_price_count:
                steel_price_count = count

        scrap = deps.price_resolver.find_scrap_price(
            db, location=location_value, year=year, month=month
        )
        scrap_price_count = 1 if scrap is not None else 0

    if year and location_value and vehicle_value:
        coverage = evaluate_process_fee_coverage(
            db,
            year=year,
            aliases=aliases or [location_value],
            vehicle_model=vehicle_value,
            version=version_value,
            part_repo=deps.part_repo,
            fee_repo=deps.process_fee_repo,
        )
        process_fee_count = coverage.fee_count
        process_fee_complete = coverage.complete

    if year and location_value:
        die_fee_count = deps.die_fee_resolver.count_for_ready(
            db,
            year=year,
            location=location_value,
            vehicle_model=vehicle_value,
        )
        gauge_fee_count = deps.gauge_fee_resolver.count_for_ready(
            db,
            location=location_value,
            vehicle_model=vehicle_value,
        )

    can_calculate = bool(
        year
        and month
        and location_value
        and vehicle_value
        and part_count > 0
        and steel_price_count > 0
        and scrap_price_count > 0
        and process_fee_complete
    )

    return StampingPartCostCalcReadyVO(
        year=year,
        month=month,
        location=location_value,
        stamping_supplier=None,
        vehicle_model=vehicle_value,
        version=version_value,
        part_count=part_count,
        steel_price_count=steel_price_count,
        scrap_price_count=scrap_price_count,
        process_fee_count=process_fee_count,
        die_fee_count=die_fee_count,
        gauge_fee_count=gauge_fee_count,
        can_calculate=can_calculate,
    )
