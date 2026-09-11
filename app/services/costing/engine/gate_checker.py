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
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate_navigate import build_navigate
from app.services.costing.engine.scope_discovery import DiscoveryResult
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.steel_price.calc.coverage import inspect_steel_coverage
from app.services.costing.steel_price.calc.models import SteelPriceCalcRequest

_USABLE = [AUDIT_PENDING, AUDIT_APPROVED, AUDIT_REJECTED]


class GateChecker:
    """§5.1 硬门禁；ok=false 时附带 navigate。"""

    def __init__(self) -> None:
        self.tonnage_repo = StampingTonnagePriceRepository()
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
            self._check_period_projects(discovery, location, year, month),
            self._check_stamping_process(discovery, location, year, month),
            self._check_tonnage_price(db, discovery, location, year, month),
            self._check_welding_unit_price(db, discovery, location, year, month),
            self._check_bom_snapshot(discovery, location, year, month),
            self._check_annual_part_price(db, discovery, location, year, month),
            self._check_packaging_transport(db, discovery, location, year, month),
        ]
        items.extend(self._check_steel_chain(db, discovery))
        items.append(self._check_scrap_price(db, discovery, location, year, month))
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

    def _skipped(
        self,
        *,
        code: str,
        message: str,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        return self._item(
            code=code,
            ok=True,
            missing=[],
            message=message,
            location=location,
            year=year,
            month=month,
        )

    def _check_period_projects(
        self,
        discovery: DiscoveryResult,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        if not discovery.vehicle_models:
            return self._item(
                code="vehicle_model",
                ok=False,
                missing=["本期没有可引入项目"],
                message="没有本期可引入项目，请到项目一览表手工增加或调整生效失效（#/vehicle-model-list）",
                location=location,
                year=year,
                month=month,
            )
        return self._item(
            code="vehicle_model",
            ok=True,
            missing=[],
            message=f"本期项目 {len(discovery.vehicle_models)} 个",
            location=location,
            year=year,
            month=month,
        )

    def _check_stamping_process(
        self,
        discovery: DiscoveryResult,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        if not discovery.vehicle_models:
            return self._item(
                code="stamping_process",
                ok=True,
                missing=[],
                message="无本期项目，未展开工艺检查",
                location=location,
                year=year,
                month=month,
            )
        part_models = set(discovery.stamping_vehicle_models)
        missing = [name for name in discovery.vehicle_models if name not in part_models]
        if missing:
            preview = "、".join(missing[:8])
            extra = f" 等 {len(missing)} 个" if len(missing) > 8 else ""
            return self._item(
                code="stamping_process",
                ok=False,
                missing=missing[:20],
                message=(
                    f"缺少冲压工艺：{preview}{extra}。"
                    "已跳过这些项目的冲压加工费与零件价；有 BOM 的仍可总成核价"
                ),
                location=location,
                year=year,
                month=month,
            )
        return self._item(
            code="stamping_process",
            ok=True,
            missing=[],
            message=f"已发现 {len(discovery.vehicle_models)} 个项目",
            location=location,
            year=year,
            month=month,
        )

    def _check_tonnage_price(
        self,
        db: Session,
        discovery: DiscoveryResult,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        if not discovery.stamping_vehicle_models:
            return self._skipped(
                code="tonnage_price",
                message="无冲压工艺，跳过冲次单价与冲压加工费检查",
                location=location,
                year=year,
                month=month,
            )
        aliases = discovery.location_aliases
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
        discovery: DiscoveryResult,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        if not discovery.l0_scopes:
            return self._skipped(
                code="welding_unit_price",
                message="无含 L0 的 BOM，跳过焊接单价与焊接加工费检查",
                location=location,
                year=year,
                month=month,
            )
        aliases = discovery.location_aliases
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
                message="缺少含 L0 的材料清单，已跳过焊接费与总成核价",
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
        discovery: DiscoveryResult,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        if not discovery.l0_scopes:
            return self._skipped(
                code="annual_part_price",
                message="无含 L0 的 BOM，跳过年度零件价检查",
                location=location,
                year=year,
                month=month,
            )
        aliases = discovery.location_aliases
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
        discovery: DiscoveryResult,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        if not discovery.l0_scopes:
            return self._skipped(
                code="packaging_transport",
                message="无含 L0 的 BOM，跳过包装运输费检查",
                location=location,
                year=year,
                month=month,
            )
        aliases = discovery.location_aliases
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
        report = inspect_steel_coverage(db, request)
        if not report.has_materials:
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

        base_item = self._item(
            code="base_price",
            ok=report.base_ok,
            missing=report.missing_base,
            message=(
                f"基价覆盖完整，展开 {report.row_count} 行"
                if report.base_ok
                else f"基价覆盖不全：{report.no_base_count} 个规格无匹配"
            ),
            location=location,
            year=year,
            month=month,
        )

        if not report.base_ok:
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

        thickness_ok = len(report.thickness_missing) == 0
        return [
            base_item,
            self._item(
                code="thickness_policy",
                ok=thickness_ok,
                missing=report.thickness_missing,
                message=(
                    "厚度加减价政策可匹配"
                    if thickness_ok
                    else (f"厚度政策匹配失败 {len(report.thickness_missing)} 项" "，须补齐后再启动")
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
        discovery: DiscoveryResult,
        location: str,
        year: int,
        month: int,
    ) -> CostingEngineGateItemVO:
        if not discovery.stamping_vehicle_models:
            return self._skipped(
                code="scrap_price",
                message="无冲压工艺，跳过废料价检查",
                location=location,
                year=year,
                month=month,
            )
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
