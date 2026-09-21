"""加工费编排依赖：仓库与计算器一次装配。"""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.stamping.part.repository import StampingPartRepository
from app.repositories.stamping.process_fee.repository import (
    StampingProcessFeeRepository,
)
from app.repositories.stamping.tonnage_price.repository import StampingTonnagePriceRepository
from app.services.stamping.process_fee.calc.calc_log import ProcessFeeCalcLogService
from app.services.stamping.process_fee.calc.part_calculator import PartFeeCalculator
from app.services.stamping.process_fee.calc.tailor_weld_calculator import (
    TailorWeldFeeCalculator,
)


@dataclass(frozen=True, slots=True)
class ProcessFeeCalcDeps:
    fee_repo: StampingProcessFeeRepository
    part_repo: StampingPartRepository
    tonnage_repo: StampingTonnagePriceRepository
    calc_log_service: ProcessFeeCalcLogService
    part_calculator: PartFeeCalculator
    tailor_weld_calculator: TailorWeldFeeCalculator


def build_process_fee_calc_deps() -> ProcessFeeCalcDeps:
    return ProcessFeeCalcDeps(
        fee_repo=StampingProcessFeeRepository(),
        part_repo=StampingPartRepository(),
        tonnage_repo=StampingTonnagePriceRepository(),
        calc_log_service=ProcessFeeCalcLogService(),
        part_calculator=PartFeeCalculator(),
        tailor_weld_calculator=TailorWeldFeeCalculator(),
    )
