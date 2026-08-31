"""焊接费计算就绪统计（按 level）。"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.schemas.vo.bom_welding_fee_vo import BomWeldingFeeCalcReadyVO, WeldingFeeLevelReadyVO
from app.services.bom.welding_fee.calc.orchestrator.deps import WeldingFeeCalcDeps


def collect_calc_ready(
    db: Session,
    deps: WeldingFeeCalcDeps,
    *,
    year: int,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> BomWeldingFeeCalcReadyVO:
    location = location.strip()
    vehicle_model = vehicle_model.strip()
    bom_version = bom_version.strip()
    prices = deps.unit_price_repo.list_by_location_year(db, location, year)
    nodes = deps.breakdown_repo.list_by_scope(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
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
        bom_version=bom_version,
        unit_price_count=len(prices),
        levels=levels,
    )
