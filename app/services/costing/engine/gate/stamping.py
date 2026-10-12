"""核价引擎门禁：项目、冲压工艺、冲次单价、模具单价。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.stamping.die.unit_price import StampingDieUnitPriceRepository
from app.repositories.stamping.tonnage_price.repository import StampingTonnagePriceRepository
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate.item import (
    USABLE_STATUSES,
    make_item,
    make_skipped,
    skip_if_period_filtered,
)
from app.services.costing.engine.scope.discovery import DiscoveryResult
from app.services.stamping.die_fee.calc.orchestrator.ready import (
    evaluate_die_fee_coverage,
)
from app.services.stamping.die_fee.rules.fee_math import ZERO


def check_period_projects(
    discovery: DiscoveryResult,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    if discovery.is_period_filtered():
        return make_item(
            code="vehicle_model_period",
            ok=False,
            missing=["该月项目未生效或已失效"],
            message="这个月的零件或材料清单，所属项目还没生效或已经失效。请到项目列表核对生效和失效。",
            location=location,
            year=year,
            month=month,
        )
    if not discovery.vehicle_models:
        return make_item(
            code="vehicle_model",
            ok=False,
            missing=["这个月没有还有效的冲压零件或材料清单"],
            message="这个月没有还有效的冲压零件或材料清单。请到零件列表或产品结构核对有效期。",
            location=location,
            year=year,
            month=month,
        )
    return make_item(
        code="vehicle_model",
        ok=True,
        missing=[],
        message=f"该月有效期内项目 {len(discovery.vehicle_models)} 个",
        location=location,
        year=year,
        month=month,
    )


def check_stamping_process(
    discovery: DiscoveryResult,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    skipped = skip_if_period_filtered(
        discovery, code="stamping_process", location=location, year=year, month=month
    )
    if skipped is not None:
        return skipped
    if not discovery.vehicle_models:
        return make_item(
            code="stamping_process",
            ok=True,
            missing=[],
            message="这个月没有还有效的冲压零件或材料清单，工艺先不查。",
            location=location,
            year=year,
            month=month,
        )
    part_models = set(discovery.stamping_vehicle_models)
    missing = [name for name in discovery.vehicle_models if name not in part_models]
    if missing:
        preview = "、".join(missing[:8])
        extra = f" 等 {len(missing)} 个" if len(missing) > 8 else ""
        return make_item(
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
    return make_item(
        code="stamping_process",
        ok=True,
        missing=[],
        message=f"该月有效冲压工艺 {len(discovery.stamping_vehicle_models)} 个项目",
        location=location,
        year=year,
        month=month,
    )


def check_tonnage_price(
    repo: StampingTonnagePriceRepository,
    db: Session,
    discovery: DiscoveryResult,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    skipped = skip_if_period_filtered(
        discovery, code="tonnage_price", location=location, year=year, month=month
    )
    if skipped is not None:
        return skipped
    if not discovery.stamping_vehicle_models:
        return make_skipped(
            code="tonnage_price",
            message="无冲压工艺，跳过冲次单价与冲压加工费检查",
            location=location,
            year=year,
            month=month,
        )
    aliases = discovery.location_aliases
    total = 0
    for alias in aliases:
        total += repo.count_by_location_year_and_statuses(
            db, location=alias, year=year, statuses=USABLE_STATUSES
        )
    if total <= 0:
        return make_item(
            code="tonnage_price",
            ok=False,
            missing=[f"{location} / {year} 无冲次单价"],
            message="缺少冲次单价，无法补算冲压加工费",
            location=location,
            year=year,
            month=month,
        )
    return make_item(
        code="tonnage_price",
        ok=True,
        missing=[],
        message=f"冲次单价 {total} 条",
        location=location,
        year=year,
        month=month,
    )


def check_die_unit_price(
    unit_price_repo: StampingDieUnitPriceRepository,
    db: Session,
    discovery: DiscoveryResult,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    """有布点年交集的项目须有生效模具单价；有无布点问 evaluate_die_fee_coverage.has_dies。"""
    skipped = skip_if_period_filtered(
        discovery, code="die_unit_price", location=location, year=year, month=month
    )
    if skipped is not None:
        return skipped
    aliases = discovery.location_aliases
    die_vehicles: list[str] = []
    for vehicle_model in discovery.vehicle_models:
        coverage = evaluate_die_fee_coverage(
            db,
            year=year,
            aliases=aliases,
            vehicle_model=vehicle_model,
        )
        if coverage.has_dies:
            die_vehicles.append(vehicle_model)
    if not die_vehicles:
        return make_skipped(
            code="die_unit_price",
            message="无该年有效模具布点，跳过模具单价与模具费检查",
            location=location,
            year=year,
            month=month,
        )
    missing: list[str] = []
    for vehicle_model in die_vehicles:
        found = False
        for alias in aliases:
            price = unit_price_repo.get_effective(db, location=alias, vehicle_model=vehicle_model)
            if (
                price is not None
                and price.allocation_qty is not None
                and price.allocation_qty > ZERO
            ):
                found = True
                break
        if not found:
            missing.append(vehicle_model)
    if missing:
        preview = "、".join(missing[:8])
        extra = f" 等 {len(missing)} 个" if len(missing) > 8 else ""
        return make_item(
            code="die_unit_price",
            ok=False,
            missing=missing[:20],
            message=f"缺少生效模具单价或分摊万台无效：{preview}{extra}",
            location=location,
            year=year,
            month=month,
        )
    return make_item(
        code="die_unit_price",
        ok=True,
        missing=[],
        message=f"模具单价已齐（{len(die_vehicles)} 个有布点项目）",
        location=location,
        year=year,
        month=month,
    )
