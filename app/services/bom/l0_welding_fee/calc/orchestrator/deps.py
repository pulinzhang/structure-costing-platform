"""焊接费编排依赖。"""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.bom.l0_welding_fee_repository import BomL0WeldingFeeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.repositories.bom.welding_unit_price_repository import BomWeldingUnitPriceRepository
from app.services.bom.l0_welding_fee.calc.calc_log_service import (
    BomL0WeldingFeeCalcLogService,
)


@dataclass(frozen=True, slots=True)
class L0WeldingFeeCalcDeps:
    fee_repo: BomL0WeldingFeeRepository
    breakdown_repo: BomWeldingProcessBreakdownRepository
    unit_price_repo: BomWeldingUnitPriceRepository
    calc_log_service: BomL0WeldingFeeCalcLogService


def build_l0_welding_fee_calc_deps() -> L0WeldingFeeCalcDeps:
    return L0WeldingFeeCalcDeps(
        fee_repo=BomL0WeldingFeeRepository(),
        breakdown_repo=BomWeldingProcessBreakdownRepository(),
        unit_price_repo=BomWeldingUnitPriceRepository(),
        calc_log_service=BomL0WeldingFeeCalcLogService(),
    )
