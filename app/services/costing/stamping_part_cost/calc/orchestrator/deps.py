"""零件核价编排依赖：仓库 / 取费 / 计算器一次装配。"""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.costing.stamping_part_cost.stamping_part_cost_calc_log_repository import (
    StampingPartCostCalcLogRepository,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.repositories.stamping.gauge_fee.repository import StampingGaugeFeeRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.repositories.stamping.process_fee.repository import (
    StampingProcessFeeRepository,
)
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.services.costing.stamping_part_cost.calc.calc_log import (
    PartCostCalcLogService,
)
from app.services.costing.stamping_part_cost.calc.fees.die import DieFeeResolver
from app.services.costing.stamping_part_cost.calc.fees.gauge import GaugeFeeResolver
from app.services.costing.stamping_part_cost.calc.fees.process import ProcessFeeResolver
from app.services.costing.stamping_part_cost.calc.part_calculator import PartCostCalculator
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.stamping_part_cost.calc.tailor_weld_calculator import (
    TailorWeldPartCostCalculator,
)
from app.services.settings.system.service import SettingsService


@dataclass(frozen=True, slots=True)
class PartCostCalcDeps:
    cost_repo: StampingPartCostRepository
    calc_log_repo: StampingPartCostCalcLogRepository
    part_repo: StampingPartRepository
    steel_repo: SteelPriceRepository
    process_fee_repo: StampingProcessFeeRepository
    settings_service: SettingsService
    price_resolver: PriceResolver
    die_fee_resolver: DieFeeResolver
    gauge_fee_resolver: GaugeFeeResolver
    part_calculator: PartCostCalculator
    tailor_weld_calculator: TailorWeldPartCostCalculator
    calc_log_service: PartCostCalcLogService


def build_part_cost_calc_deps() -> PartCostCalcDeps:
    cost_repo = StampingPartCostRepository()
    calc_log_repo = StampingPartCostCalcLogRepository()
    steel_repo = SteelPriceRepository()
    scrap_repo = StampingScrapPriceRepository()
    process_fee_repo = StampingProcessFeeRepository()
    price_resolver = PriceResolver(steel_repo=steel_repo, scrap_repo=scrap_repo)
    process_fee_resolver = ProcessFeeResolver(process_fee_repo)
    die_fee_resolver = DieFeeResolver(StampingDieFeeRepository())
    gauge_fee_resolver = GaugeFeeResolver(StampingGaugeFeeRepository())
    return PartCostCalcDeps(
        cost_repo=cost_repo,
        calc_log_repo=calc_log_repo,
        part_repo=StampingPartRepository(),
        steel_repo=steel_repo,
        process_fee_repo=process_fee_repo,
        settings_service=SettingsService(),
        price_resolver=price_resolver,
        die_fee_resolver=die_fee_resolver,
        gauge_fee_resolver=gauge_fee_resolver,
        part_calculator=PartCostCalculator(
            price_resolver=price_resolver,
            process_fee_resolver=process_fee_resolver,
            die_fee_resolver=die_fee_resolver,
            gauge_fee_resolver=gauge_fee_resolver,
        ),
        tailor_weld_calculator=TailorWeldPartCostCalculator(
            price_resolver=price_resolver,
            process_fee_resolver=process_fee_resolver,
            die_fee_resolver=die_fee_resolver,
            gauge_fee_resolver=gauge_fee_resolver,
        ),
        calc_log_service=PartCostCalcLogService(calc_log_repo=calc_log_repo),
    )
