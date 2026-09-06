"""钢价编排依赖。"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.costing.steel_price.calc.calc_log_service import CalcLogService
from app.services.costing.steel_price.calc.steps import (
    AdjustmentApplier,
    BasePriceEnricher,
    MaterialThicknessLoader,
)
from app.services.costing.steel_price.steel_price_service import SteelPriceService


@dataclass(frozen=True, slots=True)
class SteelPriceCalcDeps:
    material_loader: MaterialThicknessLoader
    base_price_enricher: BasePriceEnricher
    adjustment_applier: AdjustmentApplier
    steel_price_service: SteelPriceService
    calc_log_service: CalcLogService


def build_steel_price_calc_deps() -> SteelPriceCalcDeps:
    return SteelPriceCalcDeps(
        material_loader=MaterialThicknessLoader(),
        base_price_enricher=BasePriceEnricher(),
        adjustment_applier=AdjustmentApplier(),
        steel_price_service=SteelPriceService(),
        calc_log_service=CalcLogService(),
    )
