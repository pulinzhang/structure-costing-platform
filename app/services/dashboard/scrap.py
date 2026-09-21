"""仪表盘：废料月度价齐套状态。"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, NamedTuple

from sqlalchemy.orm import Session

from app.common.money import parse_decimal
from app.common.scrap_categories import SCRAP_CATEGORY_STEEL
from app.services.masterdata.location.service import LocationService

if TYPE_CHECKING:
    from app.services.dashboard.service import DashboardService


class ScrapStatus(NamedTuple):
    filled_count: int
    required_count: int
    is_complete: bool
    scrap_location: str | None
    is_scrap_location_filled: bool | None
    scrap_location_net_price: Decimal | None


def scrap_month_status(
    svc: DashboardService,
    db: Session,
    *,
    year: int,
    month: int,
    location: str | None = None,
) -> ScrapStatus:
    sheet = svc.scrap_service.get_month_sheet(db, year, month, SCRAP_CATEGORY_STEEL)

    scrap_location: str | None = None
    is_scrap_location_filled: bool | None = None
    scrap_location_net_price: Decimal | None = None
    if location:
        scrap_location = location
        row = next((r for r in sheet.items if r.location == location), None)
        if row is None:
            aliases = LocationService().expand_for_query(db, location)
            row = next(
                (r for r in sheet.items if r.location in aliases),
                None,
            )
        if row is not None and row.net_price is not None:
            is_scrap_location_filled = True
            scrap_location_net_price = parse_decimal(row.net_price)
        else:
            is_scrap_location_filled = False

    return ScrapStatus(
        filled_count=int(sheet.filled_count),
        required_count=int(sheet.required_count),
        is_complete=bool(sheet.is_complete),
        scrap_location=scrap_location,
        is_scrap_location_filled=is_scrap_location_filled,
        scrap_location_net_price=scrap_location_net_price,
    )
