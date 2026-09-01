"""钢材联动价 / 废料月度价匹配。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.costing import SteelPrice
from app.models.yishiyiyi import StampingScrapPrice
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.services.costing.stamping_part_cost.helpers import location_candidates


class PriceResolver:
    """按基地别名匹配废料价；钢材联动价按牌号+料厚。"""

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
        """只按年月/基地/牌号/料厚取价，不对大类回退。"""
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
                return matched
        return []

    def pick_steel_price(self, rows: list[SteelPrice]) -> SteelPrice | None:
        """同牌号同料厚多钢厂时取最低最终吨价；同价再按钢厂名、id 稳定选取。"""
        priced: list[SteelPrice] = []
        for row in rows:
            ton: object = row.final_price_per_ton
            if not isinstance(ton, Decimal):
                continue
            priced.append(row)
        if not priced:
            return None
        return min(
            priced,
            key=lambda row: (
                Decimal(str(row.final_price_per_ton)),
                (row.steel_mill or "").strip(),
                int(row.id or 0),
            ),
        )
