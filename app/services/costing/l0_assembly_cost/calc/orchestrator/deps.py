"""成品核价编排依赖。"""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.bom.annual_part_price_repository import BomAnnualPartPriceRepository
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.repositories.costing.l0_assembly_cost.l0_assembly_cost_repository import (
    L0AssemblyCostRepository,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.services.costing.l0_assembly_cost.calc.calc_log_service import (
    L0AssemblyCostCalcLogService,
)
from app.services.settings.system.settings_service import SettingsService


@dataclass(frozen=True, slots=True)
class L0AssemblyCalcDeps:
    cost_repo: L0AssemblyCostRepository
    calc_log_service: L0AssemblyCostCalcLogService
    settings_service: SettingsService
    bom_snapshot_repo: BomSnapshotRepository
    bom_node_repo: BomNodeRepository
    stamping_cost_repo: StampingPartCostRepository
    annual_price_repo: BomAnnualPartPriceRepository
    l0_welding_fee_repo: BomWeldingFeeRepository
    packaging_fee_repo: BomPackagingTransportFeeRepository


def build_l0_assembly_calc_deps() -> L0AssemblyCalcDeps:
    return L0AssemblyCalcDeps(
        cost_repo=L0AssemblyCostRepository(),
        calc_log_service=L0AssemblyCostCalcLogService(),
        settings_service=SettingsService(),
        bom_snapshot_repo=BomSnapshotRepository(),
        bom_node_repo=BomNodeRepository(),
        stamping_cost_repo=StampingPartCostRepository(),
        annual_price_repo=BomAnnualPartPriceRepository(),
        l0_welding_fee_repo=BomWeldingFeeRepository(),
        packaging_fee_repo=BomPackagingTransportFeeRepository(),
    )
