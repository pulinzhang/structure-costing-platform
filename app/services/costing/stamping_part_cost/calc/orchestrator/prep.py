"""计算开场：范围、费率、就绪、废料、零件清单。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.stamping import StampingPart
from app.models.yishiyiyi import StampingScrapPrice
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostCalcReadyVO
from app.services.costing.stamping_part_cost.calc.orchestrator.deps import PartCostCalcDeps
from app.services.costing.stamping_part_cost.calc.orchestrator.messages import (
    format_missing_scrap,
    format_no_parts,
    format_parts_matched,
    format_prep_opening,
    format_rates,
    format_ready,
    format_scrap_price,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.stamping_part_cost.calc.orchestrator.rates import (
    PartCostCalcRates,
    load_part_cost_calc_rates,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.ready import collect_calc_ready
from app.services.costing.stamping_part_cost.calc.scope import require_calc_scope
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.stamping.part.service import StampingPartService


@dataclass(frozen=True, slots=True)
class CalcPrepContext:
    location: str
    rates: PartCostCalcRates
    scrap: StampingScrapPrice
    scrap_ton_price: Decimal
    parts: list[StampingPart]
    ready: StampingPartCostCalcReadyVO
    started_at: datetime
    detail_lines: list[str]
    material_by_part_id: dict[int, str] = field(default_factory=dict)


def prepare_calc_run(
    db: Session,
    deps: PartCostCalcDeps,
    dto: StampingPartCostCalcDTO,
    progress: ProgressNotifier,
) -> CalcPrepContext:
    scope = require_calc_scope(dto)
    location, vehicle_model = VehicleModelService().require_introducible(
        db, scope.location, scope.vehicle_model, dto.year, dto.month
    )
    rates = load_part_cost_calc_rates(deps.settings_service, db)
    started_at = now()
    detail_lines = [
        format_prep_opening(dto.year, dto.month, location, vehicle_model),
        format_rates(rates),
    ]

    progress.report(5, "正在核对要用的价格…")
    ready = collect_calc_ready(
        db,
        deps,
        year=dto.year,
        month=dto.month,
        location=location,
        vehicle_model=vehicle_model,
    )
    if not ready.can_calculate:
        raise BusinessException("还不能算：钢材联动价、废料月度价、加工费和冲压零件要同时有。")
    detail_lines.append(
        format_ready(
            ready.part_count,
            ready.steel_price_count,
            ready.scrap_price_count,
            ready.process_fee_count,
            ready.die_fee_count,
            ready.gauge_fee_count,
        )
    )

    scrap = deps.price_resolver.find_scrap_price(
        db, location=location, year=dto.year, month=dto.month
    )
    if scrap is None:
        raise BusinessException(format_missing_scrap(location, dto.year, dto.month))
    scrap_ton_price = Decimal(str(scrap.net_price))
    detail_lines.append(format_scrap_price(scrap_ton_price))

    progress.report(10, "正在读取冲压零件…")
    parts = deps.part_repo.list_with_processes(
        db,
        location=location,
        vehicle_model=vehicle_model,
        as_of_year=dto.year,
        as_of_month=dto.month,
    )
    if not parts:
        raise BusinessException(format_no_parts(location, vehicle_model, dto.year, dto.month))
    detail_lines.append(format_parts_matched(len(parts)))
    material_rows = StampingPartService().list_materials_as_of(
        db,
        location=location,
        year=dto.year,
        month=dto.month,
        vehicle_model=vehicle_model,
    )
    material_by_part_id = {
        row["part_id"]: row["material"] for row in material_rows if row["blank_id"] is None
    }

    return CalcPrepContext(
        location=location,
        rates=rates,
        scrap=scrap,
        scrap_ton_price=scrap_ton_price,
        parts=parts,
        material_by_part_id=material_by_part_id,
        ready=ready,
        started_at=started_at,
        detail_lines=detail_lines,
    )
