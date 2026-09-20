"""焊接费计算就绪统计（按 level）。"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.schemas.vo.bom_welding_fee_vo import BomWeldingFeeCalcReadyVO, WeldingFeeLevelReadyVO
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.welding_fee.calc.orchestrator.deps import WeldingFeeCalcDeps
from app.services.masterdata.vehicle_model import VehicleModelService


def collect_calc_ready(
    db: Session,
    deps: WeldingFeeCalcDeps,
    *,
    year: int,
    location: str,
    vehicle_model: str,
) -> BomWeldingFeeCalcReadyVO:
    location = location.strip()
    vehicle_model = vehicle_model.strip()
    try:
        location, vehicle_model = VehicleModelService().require_overlaps_year(
            db, location, vehicle_model, year
        )
    except BusinessException as exc:
        return BomWeldingFeeCalcReadyVO(
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            unit_price_count=0,
            levels=[],
            message=str(exc),
        )
    prices = deps.unit_price_repo.list_by_location_year(db, location, year)
    nodes = deps.breakdown_repo.list_by_source_node_ids(
        db,
        list(
            BomPeriodService().node_ids_overlapping_year(
                db, location=location, vehicle_model=vehicle_model, year=year
            )
        ),
    )
    grouped: dict[int, list[int]] = defaultdict(list)
    for node in nodes:
        grouped[int(node.level)].append(int(node.process_line_count or 0))
    levels = [
        WeldingFeeLevelReadyVO(
            level=level,
            node_count=len(line_counts),
            process_line_total=sum(line_counts),
            zero_process_count=sum(1 for count in line_counts if count == 0),
        )
        for level, line_counts in sorted(grouped.items())
    ]
    return BomWeldingFeeCalcReadyVO(
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        unit_price_count=len(prices),
        levels=levels,
    )
