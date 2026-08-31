"""计算开场：范围、费率、就绪、废料、零件清单。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.stamping import StampingPart
from app.models.yishiyiyi import StampingScrapPrice
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostCalcReadyVO
from app.services.costing.stamping_part_cost.calc.constants import FORMULA_VERSION
from app.services.costing.stamping_part_cost.calc.orchestrator.deps import PartCostCalcDeps
from app.services.costing.stamping_part_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.stamping_part_cost.calc.orchestrator.rates import (
    PartCostCalcRates,
    load_part_cost_calc_rates,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.ready import collect_calc_ready
from app.services.costing.stamping_part_cost.calc.scope import require_scope


@dataclass(frozen=True, slots=True)
class CalcPrepContext:
    location: str
    supplier: str
    rates: PartCostCalcRates
    scrap: StampingScrapPrice
    scrap_ton_price: Decimal
    parts: list[StampingPart]
    ready: StampingPartCostCalcReadyVO
    started_at: datetime
    detail_lines: list[str]


def prepare_calc_run(
    db: Session,
    deps: PartCostCalcDeps,
    dto: StampingPartCostCalcDTO,
    progress: ProgressNotifier,
) -> CalcPrepContext:
    location, supplier = require_scope(dto)
    rates = load_part_cost_calc_rates(deps.settings_service, db)
    started_at = now()
    detail_lines = [
        f"开始计算 year={dto.year} month={dto.month} location={location} "
        f"supplier={supplier} density={rates.density} loss_rate={rates.loss_rate} "
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
        stamping_supplier=supplier,
        vehicle_model=dto.vehicle_model,
        version=dto.version,
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
        stamping_supplier=supplier,
        vehicle_model=dto.vehicle_model,
        version=dto.version,
    )
    if not parts:
        raise BusinessException(f"基地「{location}」工厂「{supplier}」下未找到匹配的冲压零件")
    detail_lines.append(f"匹配零件 {len(parts)} 件")

    return CalcPrepContext(
        location=location,
        supplier=supplier,
        rates=rates,
        scrap=scrap,
        scrap_ton_price=scrap_ton_price,
        parts=parts,
        ready=ready,
        started_at=started_at,
        detail_lines=detail_lines,
    )
