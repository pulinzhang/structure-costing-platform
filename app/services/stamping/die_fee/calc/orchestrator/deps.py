"""模具费编排依赖。"""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.stamping.die.repository import StampingDiePartRepository
from app.repositories.stamping.die.unit_price import StampingDieUnitPriceRepository
from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.services.stamping.die_fee.calc.calc_log import DieFeeCalcLogService
from app.services.stamping.die_fee.calc.part_calculator import DieFeePartCalculator


@dataclass(frozen=True, slots=True)
class DieFeeCalcDeps:
    fee_repo: StampingDieFeeRepository
    die_repo: StampingDiePartRepository
    unit_price_repo: StampingDieUnitPriceRepository
    part_repo: StampingPartRepository
    calc_log_service: DieFeeCalcLogService
    part_calculator: DieFeePartCalculator


def build_die_fee_calc_deps() -> DieFeeCalcDeps:
    return DieFeeCalcDeps(
        fee_repo=StampingDieFeeRepository(),
        die_repo=StampingDiePartRepository(),
        unit_price_repo=StampingDieUnitPriceRepository(),
        part_repo=StampingPartRepository(),
        calc_log_service=DieFeeCalcLogService(),
        part_calculator=DieFeePartCalculator(),
    )
