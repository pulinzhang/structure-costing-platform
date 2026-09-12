"""核价引擎门禁：废料月度价。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate.item import make_item, make_skipped
from app.services.costing.engine.scope_discovery import DiscoveryResult
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver


def check_scrap_price(
    resolver: PriceResolver,
    db: Session,
    discovery: DiscoveryResult,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    if not discovery.stamping_vehicle_models:
        return make_skipped(
            code="scrap_price",
            message="无冲压工艺，跳过废料价检查",
            location=location,
            year=year,
            month=month,
        )
    scrap = resolver.find_scrap_price(db, location=location, year=year, month=month)
    if scrap is None:
        return make_item(
            code="scrap_price",
            ok=False,
            missing=[f"{location} / {year}-{month:02d} 无废料月度价"],
            message="缺少废料月度销售价",
            location=location,
            year=year,
            month=month,
        )
    return make_item(
        code="scrap_price",
        ok=True,
        missing=[],
        message="废料月度价已就绪",
        location=location,
        year=year,
        month=month,
    )
