"""核价引擎门禁：焊接单价。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.bom.welding_unit_price_repository import BomWeldingUnitPriceRepository
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate.item import (
    USABLE_STATUSES,
    make_item,
    make_skipped,
    skip_if_period_filtered,
)
from app.services.costing.engine.scope.discovery import DiscoveryResult


def check_welding_unit_price(
    repo: BomWeldingUnitPriceRepository,
    db: Session,
    discovery: DiscoveryResult,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    skipped = skip_if_period_filtered(
        discovery, code="welding_unit_price", location=location, year=year, month=month
    )
    if skipped is not None:
        return skipped
    if not discovery.l0_scopes:
        return make_skipped(
            code="welding_unit_price",
            message="无含 L0 的 BOM，跳过焊接单价与焊接加工费检查",
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
            code="welding_unit_price",
            ok=False,
            missing=[f"{location} / {year} 无焊接单价"],
            message="缺少焊接单价",
            location=location,
            year=year,
            month=month,
        )
    return make_item(
        code="welding_unit_price",
        ok=True,
        missing=[],
        message=f"焊接单价 {total} 条",
        location=location,
        year=year,
        month=month,
    )
