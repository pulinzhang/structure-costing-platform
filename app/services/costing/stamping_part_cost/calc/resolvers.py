"""钢材联动价 / 废料月度价匹配。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.stamping_scrap_price import StampingScrapPrice
from app.models.steel_price import SteelPrice
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.services.costing.stamping_part_cost.helpers import location_candidates


class PriceResolver:
    """按基地别名匹配废料价与钢材联动价。"""

    def __init__(
        self,
        steel_repo: SteelPriceRepository | None = None,
        scrap_repo: StampingScrapPriceRepository | None = None,
    ) -> None:
        self.steel_repo = steel_repo or SteelPriceRepository()
        self.scrap_repo = scrap_repo or StampingScrapPriceRepository()

    def find_scrap_price(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        month: int,
    ) -> StampingScrapPrice | None:
        for candidate in location_candidates(location):
            # 废料表通常存短名（芜湖）；优先短名
            short = candidate[:-2] if candidate.endswith("基地") else candidate
            record = self.scrap_repo.get_by_location_year_month(
                db, location=short, year=year, month=month
            )
            if record is not None:
                return record
            record = self.scrap_repo.get_by_location_year_month(
                db, location=candidate, year=year, month=month
            )
            if record is not None:
                return record
        return None

    def find_steel_prices(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        grade: str,
        thickness: Decimal,
    ) -> list[SteelPrice]:
        rows: list[SteelPrice] = []
        for candidate in location_candidates(location):
            matched = self.steel_repo.list_by_grade_thickness(
                db,
                year=year,
                month=month,
                location=candidate,
                grade=grade,
                thickness=thickness,
            )
            if matched:
                rows.extend(matched)
                break
        return rows
