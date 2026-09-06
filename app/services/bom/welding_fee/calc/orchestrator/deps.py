"""焊接费编排依赖。"""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.repositories.bom.welding_unit_price_repository import BomWeldingUnitPriceRepository
from app.services.bom.welding_fee.calc.calc_log_service import (
    BomWeldingFeeCalcLogService,
)


@dataclass(frozen=True, slots=True)
class WeldingFeeCalcDeps:
    fee_repo: BomWeldingFeeRepository
    breakdown_repo: BomWeldingProcessBreakdownRepository
    unit_price_repo: BomWeldingUnitPriceRepository
    calc_log_service: BomWeldingFeeCalcLogService


def build_welding_fee_calc_deps() -> WeldingFeeCalcDeps:
    return WeldingFeeCalcDeps(
        fee_repo=BomWeldingFeeRepository(),
        breakdown_repo=BomWeldingProcessBreakdownRepository(),
        unit_price_repo=BomWeldingUnitPriceRepository(),
        calc_log_service=BomWeldingFeeCalcLogService(),
    )
