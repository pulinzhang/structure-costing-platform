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
from app.services.costing.stamping_part_cost.calc.constants import (
    ALL_SUPPLIERS_LOCK,
    FORMULA_VERSION,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.deps import PartCostCalcDeps
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
        f"开始计算 year={dto.year} month={dto.month} location={location} "
        f"supplier={ALL_SUPPLIERS_LOCK} vehicle_model={vehicle_model} "
        f"density={rates.density} loss_rate={rates.loss_rate} "
        f"recovery={rates.recovery_rate} finance={rates.finance_rate} "
        f"management={rates.management_rate} "
        f"warehouse_packaging={rates.warehouse_packaging_rate} "
        f"pretax_profit={rates.pretax_profit_rate} formula={FORMULA_VERSION}"
    ]

    progress.report(5, "校验前置数据...")
    ready = collect_calc_ready(
        db,
        deps,
        year=dto.year,
        month=dto.month,
        location=location,
        vehicle_model=vehicle_model,
    )
    if not ready.can_calculate:
        raise BusinessException(
            "前置数据未齐：须同时具备钢材联动价、废料月度价、加工费结果与匹配零件"
        )
    detail_lines.append(
        f"就绪：零件 {ready.part_count}，钢材价 {ready.steel_price_count}，"
        f"废料价 {ready.scrap_price_count}，加工费 {ready.process_fee_count}，"
        f"模具费 {ready.die_fee_count}，检具费 {ready.gauge_fee_count}"
    )

    scrap = deps.price_resolver.find_scrap_price(
        db, location=location, year=dto.year, month=dto.month
    )
    if scrap is None:
        raise BusinessException(f"基地「{location}」{dto.year}-{dto.month:02d} 无废料月度销售价")
    scrap_ton_price = Decimal(str(scrap.net_price))
    detail_lines.append(
        f"废料净价 {scrap_ton_price} 元/吨 (id={scrap.id}, location={scrap.location})"
    )

    progress.report(10, "加载冲压零件...")
    parts = deps.part_repo.list_with_processes(
        db,
        location=location,
        vehicle_model=vehicle_model,
        as_of_year=dto.year,
        as_of_month=dto.month,
    )
    if not parts:
        raise BusinessException(
            f"基地「{location}」项目「{vehicle_model}」在 {dto.year} 年 {dto.month:02d} 月"
            "没有有效期内的冲压零件"
        )
    detail_lines.append(f"匹配零件 {len(parts)} 件")
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
