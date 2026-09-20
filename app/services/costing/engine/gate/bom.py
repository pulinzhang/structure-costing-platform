"""核价引擎门禁：BOM 快照、年度零件价、包装运输费。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.bom.annual_part_price_repository import BomAnnualPartPriceRepository
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate.item import (
    USABLE_STATUSES,
    make_item,
    make_skipped,
    skip_if_period_filtered,
)
from app.services.costing.engine.scope.discovery import DiscoveryResult


def check_bom_snapshot(
    discovery: DiscoveryResult,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    skipped = skip_if_period_filtered(
        discovery, code="bom_snapshot", location=location, year=year, month=month
    )
    if skipped is not None:
        return skipped
    if not discovery.l0_scopes:
        return make_item(
            code="bom_snapshot",
            ok=False,
            missing=["该月没有有效期内的 L0 树"],
            message="该月没有有效期内的 L0 树，已跳过焊接费与总成核价",
            location=location,
            year=year,
            month=month,
        )
    labels = [f"{s.vehicle_model}/{s.bom_version}" for s in discovery.l0_scopes]
    return make_item(
        code="bom_snapshot",
        ok=True,
        missing=[],
        message=f"含 L0 的 BOM {len(labels)} 版：" + "、".join(labels[:8]),
        location=location,
        year=year,
        month=month,
    )


def check_annual_part_price(
    repo: BomAnnualPartPriceRepository,
    db: Session,
    discovery: DiscoveryResult,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    skipped = skip_if_period_filtered(
        discovery, code="annual_part_price", location=location, year=year, month=month
    )
    if skipped is not None:
        return skipped
    if not discovery.l0_scopes:
        return make_skipped(
            code="annual_part_price",
            message="无含 L0 的 BOM，跳过年度零件价检查",
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
            code="annual_part_price",
            ok=False,
            missing=[f"{location} / {year} 无年度零件价"],
            message="缺少年度零件价",
            location=location,
            year=year,
            month=month,
        )
    return make_item(
        code="annual_part_price",
        ok=True,
        missing=[],
        message=f"年度零件价 {total} 条",
        location=location,
        year=year,
        month=month,
    )


def check_packaging_transport(
    repo: BomPackagingTransportFeeRepository,
    db: Session,
    discovery: DiscoveryResult,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    skipped = skip_if_period_filtered(
        discovery, code="packaging_transport", location=location, year=year, month=month
    )
    if skipped is not None:
        return skipped
    if not discovery.l0_scopes:
        return make_skipped(
            code="packaging_transport",
            message="无含 L0 的 BOM，跳过包装运输费检查",
            location=location,
            year=year,
            month=month,
        )
    aliases = discovery.location_aliases
    total = 0
    for alias in aliases:
        _, count = repo.paginate(db, location=alias, year=year, skip=0, limit=1)
        total += count
    if total <= 0:
        return make_item(
            code="packaging_transport",
            ok=False,
            missing=[f"{location} / {year} 无包装运输费"],
            message="缺少包装运输费",
            location=location,
            year=year,
            month=month,
        )
    return make_item(
        code="packaging_transport",
        ok=True,
        missing=[],
        message=f"包装运输费约 {total} 条",
        location=location,
        year=year,
        month=month,
    )
