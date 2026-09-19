"""核价引擎 — 上传/配置硬门禁（门面，符号路径保持不变）。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.bom.annual_part_price_repository import BomAnnualPartPriceRepository
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.repositories.bom.welding_unit_price_repository import BomWeldingUnitPriceRepository
from app.repositories.settings.system.system_config_repository import SystemConfigRepository
from app.repositories.stamping.die_unit_price_repository import StampingDieUnitPriceRepository
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate.bom import (
    check_annual_part_price,
    check_bom_snapshot,
    check_packaging_transport,
)
from app.services.costing.engine.gate.rates import check_system_rates
from app.services.costing.engine.gate.scrap import check_scrap_price
from app.services.costing.engine.gate.stamping import (
    check_die_unit_price,
    check_period_projects,
    check_stamping_process,
    check_tonnage_price,
)
from app.services.costing.engine.gate.steel import check_steel_chain
from app.services.costing.engine.gate.welding import check_welding_unit_price
from app.services.costing.engine.scope_discovery import DiscoveryResult
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver


class GateChecker:
    """§5.1 硬门禁；ok=false 时附带 navigate。"""

    def __init__(self) -> None:
        self.tonnage_repo = StampingTonnagePriceRepository()
        self.die_unit_price_repo = StampingDieUnitPriceRepository()
        self.welding_unit_repo = BomWeldingUnitPriceRepository()
        self.annual_part_repo = BomAnnualPartPriceRepository()
        self.packaging_repo = BomPackagingTransportFeeRepository()
        self.system_config_repo = SystemConfigRepository()
        self.price_resolver = PriceResolver()

    def check(
        self,
        db: Session,
        discovery: DiscoveryResult,
    ) -> list[CostingEngineGateItemVO]:
        location = discovery.location
        year = discovery.year
        month = discovery.month
        items = [
            check_period_projects(discovery, location, year, month),
            check_stamping_process(discovery, location, year, month),
            check_tonnage_price(self.tonnage_repo, db, discovery, location, year, month),
            check_die_unit_price(
                self.die_unit_price_repo,
                db,
                discovery,
                location,
                year,
                month,
            ),
            check_welding_unit_price(self.welding_unit_repo, db, discovery, location, year, month),
            check_bom_snapshot(discovery, location, year, month),
            check_annual_part_price(self.annual_part_repo, db, discovery, location, year, month),
            check_packaging_transport(self.packaging_repo, db, discovery, location, year, month),
        ]
        items.extend(check_steel_chain(db, discovery))
        items.append(check_scrap_price(self.price_resolver, db, discovery, location, year, month))
        items.append(check_system_rates(self.system_config_repo, db, location, year, month))
        return items

    def _check_tonnage_price(
        self, db: Session, discovery: DiscoveryResult, location: str, year: int, month: int
    ) -> CostingEngineGateItemVO:
        return check_tonnage_price(self.tonnage_repo, db, discovery, location, year, month)

    def _check_welding_unit_price(
        self, db: Session, discovery: DiscoveryResult, location: str, year: int, month: int
    ) -> CostingEngineGateItemVO:
        return check_welding_unit_price(
            self.welding_unit_repo, db, discovery, location, year, month
        )

    def _check_annual_part_price(
        self, db: Session, discovery: DiscoveryResult, location: str, year: int, month: int
    ) -> CostingEngineGateItemVO:
        return check_annual_part_price(self.annual_part_repo, db, discovery, location, year, month)
