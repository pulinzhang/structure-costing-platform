"""加工费计算就绪统计。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeCalcReadyVO
from app.services.stamping.process_fee.calc.orchestrator.deps import ProcessFeeCalcDeps


def collect_calc_ready(
    db: Session,
    deps: ProcessFeeCalcDeps,
    *,
    year: int,
    location: str | None = None,
    vehicle_model: str | None = None,
    version: str | None = None,
) -> StampingProcessFeeCalcReadyVO:
    if location:
        rates = deps.tonnage_repo.list_by_location_year(db, location, year)
    else:
        rates = deps.tonnage_repo.list_by_year(db, year)
    parts = []
    if location:
        parts = deps.part_repo.list_with_processes(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
        )
    return StampingProcessFeeCalcReadyVO(
        year=year,
        location=location,
        stamping_supplier=None,
        vehicle_model=vehicle_model,
        version=version,
        part_count=len(parts),
        tonnage_rate_count=len(rates),
    )
