"""焊接费计算就绪统计。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.bom_l0_welding_fee_vo import BomL0WeldingFeeCalcReadyVO
from app.services.bom.l0_welding_fee.calc.orchestrator.deps import L0WeldingFeeCalcDeps


def collect_calc_ready(
    db: Session,
    deps: L0WeldingFeeCalcDeps,
    *,
    year: int,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> BomL0WeldingFeeCalcReadyVO:
    location = location.strip()
    vehicle_model = vehicle_model.strip()
    bom_version = bom_version.strip()
    prices = deps.unit_price_repo.list_by_location_year(db, location, year)
    l0_count = deps.breakdown_repo.count_by_filters(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        level=0,
    )
    l0_process_line_total = deps.breakdown_repo.sum_process_line_count_by_filters(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        level=0,
    )
    zero_process_l0_count = deps.breakdown_repo.count_by_filters(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        level=0,
        process_line_count_eq=0,
    )
    return BomL0WeldingFeeCalcReadyVO(
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        l0_count=l0_count,
        unit_price_count=len(prices),
        l0_process_line_total=l0_process_line_total,
        zero_process_l0_count=zero_process_l0_count,
    )
