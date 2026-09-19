"""核价引擎门禁：项目、冲压工艺、冲次单价。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate.item import (
    USABLE_STATUSES,
    make_item,
    make_skipped,
    skip_if_period_filtered,
)
from app.services.costing.engine.scope_discovery import DiscoveryResult


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
            message=("该月命中的零件或 BOM 树所属项目未生效或已失效，" "请到项目一览核对生效/失效"),
            location=location,
            year=year,
            month=month,
        )
    if not discovery.vehicle_models:
        return make_item(
            code="vehicle_model",
            ok=False,
            missing=["该月没有有效期内的冲压零件或 BOM 树"],
            message=("该月没有有效期内的冲压零件或 BOM 树，" "请到零件列表或产品结构核对有效期"),
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
            message="该月没有有效期内的冲压零件或 BOM 树，未展开工艺检查",
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
