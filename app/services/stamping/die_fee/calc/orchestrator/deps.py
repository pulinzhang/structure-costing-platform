"""模具费编排依赖。"""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.stamping.die_fee_repository import StampingDieFeeRepository
from app.repositories.stamping.die_unit_price_repository import StampingDieUnitPriceRepository
from app.repositories.stamping.stamping_die_repository import StampingDiePartRepository
from app.services.stamping.die_fee.calc.calc_log_service import DieFeeCalcLogService
from app.services.stamping.die_fee.calc.part_calculator import DieFeePartCalculator


@dataclass(frozen=True, slots=True)
class DieFeeCalcDeps:
    fee_repo: StampingDieFeeRepository
    die_repo: StampingDiePartRepository
    unit_price_repo: StampingDieUnitPriceRepository
    calc_log_service: DieFeeCalcLogService
    part_calculator: DieFeePartCalculator


def build_die_fee_calc_deps() -> DieFeeCalcDeps:
    return DieFeeCalcDeps(
        fee_repo=StampingDieFeeRepository(),
        die_repo=StampingDiePartRepository(),
        unit_price_repo=StampingDieUnitPriceRepository(),
        calc_log_service=DieFeeCalcLogService(),
        part_calculator=DieFeePartCalculator(),
    )
