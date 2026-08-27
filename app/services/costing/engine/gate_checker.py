"""核价引擎 — 上传/配置硬门禁。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.repositories.bom.annual_part_price_repository import BomAnnualPartPriceRepository
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.repositories.bom.welding_unit_price_repository import BomWeldingUnitPriceRepository
from app.repositories.settings.system.system_config_repository import SystemConfigRepository
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate_navigate import build_navigate
from app.services.costing.engine.scope_discovery import DiscoveryResult
from app.services.costing.steel_price.calc.models import SteelPriceCalcRequest
from app.services.costing.steel_price.calc.steps import (
    AdjustmentApplier,
    BasePriceEnricher,
    MaterialThicknessLoader,
)
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.stamping_part_cost.helpers import location_candidates

_USABLE = [AUDIT_PENDING, AUDIT_APPROVED, AUDIT_REJECTED]


class GateChecker:
    """§5.1 硬门禁；ok=false 时附带 navigate。"""

    def __init__(self) -> None:
        self.part_repo = StampingPartRepository()
        self.tonnage_repo = StampingTonnagePriceRepository()
        self.welding_unit_repo = BomWeldingUnitPriceRepository()
        self.annual_part_repo = BomAnnualPartPriceRepository()
        self.packaging_repo = BomPackagingTransportFeeRepository()
        self.system_config_repo = SystemConfigRepository()
        self.material_loader = MaterialThicknessLoader()
        self.base_price_enricher = BasePriceEnricher()
        self.adjustment_applier = AdjustmentApplier()
        self.price_resolver = PriceResolver()

    def check(
        self,
        db: Session,
        discovery: DiscoveryResult,
    ) -> list[CostingEngineGateItemVO]:
        location = discovery.location
        year = discovery.year
        month = discovery.month
        aliases = discovery.location_aliases or location_candidates(location)

        items = [
            self._check_stamping_process(discovery, location, year, month),
            self._check_tonnage_price(db, aliases, location, year, month),
            self._check_welding_unit_price(db, aliases, location, year, month),
            self._check_bom_snapshot(discovery, location, year, month),
            self._check_annual_part_price(db, aliases, location, year, month),
            self._check_packaging_transport(db, aliases, location, year, month),
        ]
        items.extend(self._check_steel_chain(db, discovery))
        items.append(self._check_scrap_price(db, location, year, month))
        items.append(self._check_system_rates(db, location, year, month))
        return items

    def _item(
        self,
        *,
        code: str,
        ok: bool,
        missing: list[str],
        message: str,
        location: str,
        year: int,
        month: int,
        with_navigate: bool | None = None,
    ) -> CostingEngineGateItemVO:
        # 默认：失败项带跳转；可强制给「软提示」也带 navigate
        attach_nav = (not ok) if with_navigate is None else with_navigate
        navigate = None
        if attach_nav:
            navigate = build_navigate(code, year=year, month=month, location=location)
        return CostingEngineGateItemVO(
            code=code,
            ok=ok,
            missing=missing,
            message=message,
            navigate=navigate,
        )

    def _check_stamping_process(
        self,
        discovery: DiscoveryResult,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        if not discovery.stamping_suppliers:
            return self._item(
                code="stamping_process",
                ok=False,
                missing=["未发现该基地下冲压工艺零件"],
                message="缺少冲压工艺零件/工序数据，无法展开工厂计划",
                location=location,
                year=year,
                month=month,
            )
        return self._item(
            code="stamping_process",
            ok=True,
            missing=[],
            message=f"已发现 {len(discovery.stamping_suppliers)} 个冲压工厂",
            location=location,
            year=year,
            month=month,
        )

    def _check_tonnage_price(
        self,
        db: Session,
        aliases: list[str],
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        total = 0
        for alias in aliases:
            total += self.tonnage_repo.count_by_location_year_and_statuses(
                db, location=alias, year=year, statuses=_USABLE
            )
        if total <= 0:
            return self._item(
                code="tonnage_price",
                ok=False,
                missing=[f"{location} / {year} 无冲次单价"],
                message="缺少冲次单价，无法补算冲压加工费",
                location=location,
                year=year,
                month=month,
            )
        return self._item(
            code="tonnage_price",
            ok=True,
            missing=[],
            message=f"冲次单价 {total} 条",
            location=location,
            year=year,
            month=month,
        )

    def _check_welding_unit_price(
        self,
        db: Session,
        aliases: list[str],
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        total = 0
        for alias in aliases:
            total += self.welding_unit_repo.count_by_location_year_and_statuses(
                db, location=alias, year=year, statuses=_USABLE
            )
        if total <= 0:
            return self._item(
                code="welding_unit_price",
                ok=False,
                missing=[f"{location} / {year} 无焊接单价"],
                message="缺少焊接单价",
                location=location,
                year=year,
                month=month,
            )
        return self._item(
            code="welding_unit_price",
            ok=True,
            missing=[],
            message=f"焊接单价 {total} 条",
            location=location,
            year=year,
            month=month,
        )

    def _check_bom_snapshot(
        self,
        discovery: DiscoveryResult,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        if not discovery.l0_scopes:
            return self._item(
                code="bom_snapshot",
                ok=False,
                missing=["未发现含 L0 的 BOM 快照"],
                message="缺少含 L0 的材料清单版本，无法成品核价",
                location=location,
                year=year,
                month=month,
            )
        labels = [f"{s.vehicle_model}/{s.bom_version}" for s in discovery.l0_scopes]
        return self._item(
            code="bom_snapshot",
            ok=True,
            missing=[],
            message=f"含 L0 的 BOM {len(labels)} 版：" + "、".join(labels[:8]),
            location=location,
            year=year,
            month=month,
        )

    def _check_annual_part_price(
        self,
        db: Session,
        aliases: list[str],
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        total = 0
        for alias in aliases:
            total += self.annual_part_repo.count_by_location_year_and_statuses(
                db, location=alias, year=year, statuses=_USABLE
            )
        if total <= 0:
            return self._item(
                code="annual_part_price",
                ok=False,
                missing=[f"{location} / {year} 无年度零件价"],
                message="缺少年度零件价",
                location=location,
                year=year,
                month=month,
            )
        return self._item(
            code="annual_part_price",
            ok=True,
            missing=[],
            message=f"年度零件价 {total} 条",
            location=location,
            year=year,
            month=month,
        )

    def _check_packaging_transport(
        self,
        db: Session,
        aliases: list[str],
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        total = 0
        for alias in aliases:
            _, count = self.packaging_repo.paginate(db, location=alias, year=year, skip=0, limit=1)
            total += count
        if total <= 0:
            return self._item(
                code="packaging_transport",
                ok=False,
                missing=[f"{location} / {year} 无包装运输费"],
                message="缺少包装运输费",
                location=location,
                year=year,
                month=month,
            )
        return self._item(
            code="packaging_transport",
            ok=True,
            missing=[],
            message=f"包装运输费约 {total} 条",
            location=location,
            year=year,
            month=month,
        )

    def _check_steel_chain(
        self,
        db: Session,
        discovery: DiscoveryResult,
    ) -> list[CostingEngineGateItemVO]:
        location = discovery.location
        year = discovery.year
        month = discovery.month
        request = SteelPriceCalcRequest(year=year, month=month, location=location)
        materials = self.material_loader.load(db, request)
        if not materials:
            # 无材料规格时钢价链无可覆盖对象：仍视为可过（工艺门禁会另拦）
            ok_msg = "无材料规格，跳过钢种覆盖检查"
            return [
                self._item(
                    code="base_price",
                    ok=True,
                    missing=[],
                    message=ok_msg,
                    location=location,
                    year=year,
                    month=month,
                ),
                self._item(
                    code="thickness_policy",
                    ok=True,
                    missing=[],
                    message=ok_msg,
                    location=location,
                    year=year,
                    month=month,
                ),
            ]

        rows, no_base_count, no_base_details = self.base_price_enricher.enrich(
            db, request, materials
        )
        missing_base = no_base_details[:20]
        base_ok = no_base_count == 0 and len(rows) > 0
        if no_base_count == 0 and len(rows) == 0:
            base_ok = False
            missing_base = ["材料有规格但未展开任何基价行"]

        base_item = self._item(
            code="base_price",
            ok=base_ok,
            missing=missing_base,
            message=(
                f"基价覆盖完整，展开 {len(rows)} 行"
                if base_ok
                else f"基价覆盖不全：{no_base_count} 个规格无匹配"
            ),
            location=location,
            year=year,
            month=month,
        )

        if not base_ok:
            # 无完整基价则厚度无法可靠检查：仅提示，不硬停（基价项本身会硬停）
            return [
                base_item,
                self._item(
                    code="thickness_policy",
                    ok=True,
                    missing=["基价未覆盖完整，厚度政策未完整校验"],
                    message="基价未齐时跳过厚度硬校验（不阻断；可先补基价与厚度政策）",
                    location=location,
                    year=year,
                    month=month,
                    with_navigate=True,
                ),
            ]

        policies = self.adjustment_applier.load_policies(db, request)
        thickness_missing: list[str] = []

        for row in rows:
            self.adjustment_applier.apply_thickness(db, [row], policies)
            if row.thickness_policy_id is None:
                thickness_missing.append(f"{row.grade}@{float(row.thickness):.4f}/{row.steel_mill}")

        thickness_missing = list(dict.fromkeys(thickness_missing))[:20]
        thickness_ok = len(thickness_missing) == 0

        return [
            base_item,
            self._item(
                code="thickness_policy",
                # 厚度缺口只提示，允许启动引擎；钢价计算仍按现网匹配逻辑
                ok=True,
                missing=thickness_missing,
                message=(
                    "厚度加减价政策可匹配"
                    if thickness_ok
                    else (
                        f"厚度政策匹配失败 {len(thickness_missing)} 项"
                        "（不阻断启动，建议去上传厚度加减价政策）"
                    )
                ),
                location=location,
                year=year,
                month=month,
                with_navigate=not thickness_ok,
            ),
        ]

    def _check_scrap_price(
        self,
        db: Session,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        scrap = self.price_resolver.find_scrap_price(db, location=location, year=year, month=month)
        if scrap is None:
            return self._item(
                code="scrap_price",
                ok=False,
                missing=[f"{location} / {year}-{month:02d} 无废料月度价"],
                message="缺少废料月度销售价",
                location=location,
                year=year,
                month=month,
            )
        return self._item(
            code="scrap_price",
            ok=True,
            missing=[],
            message="废料月度价已就绪",
            location=location,
            year=year,
            month=month,
        )

    def _check_system_rates(
        self,
        db: Session,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        config = self.system_config_repo.get_singleton(db)
        if config is None:
            return self._item(
                code="system_rates",
                ok=False,
                missing=["系统配置单例不存在"],
                message="缺少系统费率等配置",
                location=location,
                year=year,
                month=month,
            )
        return self._item(
            code="system_rates",
            ok=True,
            missing=[],
            message="系统费率配置已就绪",
            location=location,
            year=year,
            month=month,
        )
