"""成品核价编排依赖。"""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.bom.annual_part_price_repository import BomAnnualPartPriceRepository
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.costing.assembly_cost.assembly_cost_repository import (
    AssemblyCostRepository,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.services.costing.assembly_cost.calc.calc_log_service import (
    AssemblyCostCalcLogService,
)
from app.services.settings.system.settings_service import SettingsService


@dataclass(frozen=True, slots=True)
class AssemblyCalcDeps:
    cost_repo: AssemblyCostRepository
    calc_log_service: AssemblyCostCalcLogService
    settings_service: SettingsService
    stamping_cost_repo: StampingPartCostRepository
    annual_price_repo: BomAnnualPartPriceRepository
    l0_welding_fee_repo: BomWeldingFeeRepository
    welding_fee_repo: BomWeldingFeeRepository
    packaging_fee_repo: BomPackagingTransportFeeRepository


def build_assembly_calc_deps() -> AssemblyCalcDeps:
    return AssemblyCalcDeps(
        cost_repo=AssemblyCostRepository(),
        calc_log_service=AssemblyCostCalcLogService(),
        settings_service=SettingsService(),
        stamping_cost_repo=StampingPartCostRepository(),
        annual_price_repo=BomAnnualPartPriceRepository(),
        l0_welding_fee_repo=BomWeldingFeeRepository(),
        welding_fee_repo=BomWeldingFeeRepository(),
        packaging_fee_repo=BomPackagingTransportFeeRepository(),
    )
