"""钢价编排依赖。"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.costing.steel_price.calc.calc_log import CalcLogService
from app.services.costing.steel_price.calc.steps.apply_adjustments import AdjustmentApplier
from app.services.costing.steel_price.calc.steps.enrich_base_price import BasePriceEnricher
from app.services.costing.steel_price.calc.steps.load_materials import MaterialThicknessLoader
from app.services.costing.steel_price.service import SteelPriceService


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
