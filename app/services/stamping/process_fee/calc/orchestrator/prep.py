"""计算开场：范围、冲次单价、零件清单。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.stamping import StampingPart
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeCalcDTO
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.stamping.process_fee.calc.models import TonnageRateInfo
from app.services.stamping.process_fee.calc.orchestrator.deps import ProcessFeeCalcDeps
from app.services.stamping.process_fee.calc.orchestrator.messages import (
    format_parts_matched,
    format_prep_opening,
    format_rate_loaded,
)
from app.services.stamping.process_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.stamping.process_fee.rules.scope import ALL_SUPPLIERS_LOCK, require_calc_scope


@dataclass(slots=True)
class CalcPrepContext:
    location: str
    rate_map: dict[int, TonnageRateInfo]
    parts: list[StampingPart]
    started_at: datetime
    detail_lines: list[str]


def prepare_calc_run(
    db: Session,
    deps: ProcessFeeCalcDeps,
    dto: StampingProcessFeeCalcDTO,
    progress: ProgressNotifier,
) -> CalcPrepContext:
    scope = require_calc_scope(dto)
    location, vehicle_model = VehicleModelService().require_overlaps_year(
        db, scope.location, scope.vehicle_model, dto.year
    )
    started_at = now()
    detail_lines = [format_prep_opening(dto.year, location, ALL_SUPPLIERS_LOCK)]

    progress.report(5, "加载冲次单价...")
    rates = deps.tonnage_repo.list_by_location_year(db, location, dto.year)
    if not rates:
        raise BusinessException(
            f"基地「{location}」年度 {dto.year} 无冲次单价数据，请先维护冲次单价"
        )

    rate_map: dict[int, TonnageRateInfo] = {
        int(r.tonnage): TonnageRateInfo(
            price_per_stroke=Decimal(str(r.price_per_stroke)),
            tonnage_price_id=r.id,
        )
        for r in rates
    }
    detail_lines.append(format_rate_loaded(len(rates)))

    progress.report(10, "加载冲压零件...")
    parts = deps.part_repo.list_with_processes(
        db,
        location=location,
        vehicle_model=vehicle_model,
        version=scope.version,
        overlap_year=dto.year,
    )
    if not parts:
        raise BusinessException(
            f"基地「{location}」项目「{vehicle_model}」在 {dto.year} 年没有有效期内的冲压零件"
        )
    detail_lines.append(format_parts_matched(len(parts)))

    return CalcPrepContext(
        location=location,
        rate_map=rate_map,
        parts=parts,
        started_at=started_at,
        detail_lines=detail_lines,
    )
