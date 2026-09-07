"""钢材联动价 — 只读查询 / 查询聚合。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.costing.steel_price import SteelPrice
from app.repositories.llm.location_in import location_in_clause
from app.services.llm._money import ym_int


@dataclass(frozen=True, slots=True)
class SteelMonthlyAvgRow:
    year: int
    month: int
    location: str
    row_count: int
    avg_final_price: Decimal
    min_final_price: Decimal
    max_final_price: Decimal


class SteelPriceAnalysisRepository:
    def query_monthly_avg(
        self,
        db: Session,
        *,
        location: str | None,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
    ) -> list[SteelMonthlyAvgRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = SteelPrice.year * 100 + SteelPrice.month

        q = db.query(
            SteelPrice.year,
            SteelPrice.month,
            SteelPrice.location,
            func.count(SteelPrice.id),
            func.coalesce(func.avg(SteelPrice.final_price_per_ton), 0),
            func.coalesce(func.min(SteelPrice.final_price_per_ton), 0),
            func.coalesce(func.max(SteelPrice.final_price_per_ton), 0),
        ).filter(ym_expr >= start, ym_expr <= end)

        loc_filter = location_in_clause(db, SteelPrice.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)

        q = q.group_by(
            SteelPrice.year,
            SteelPrice.month,
            SteelPrice.location,
        ).order_by(SteelPrice.year.asc(), SteelPrice.month.asc())

        return [
            SteelMonthlyAvgRow(
                year=int(item[0]),
                month=int(item[1]),
                location=str(item[2]),
                row_count=int(item[3] or 0),
                avg_final_price=Decimal(str(item[4] or 0)),
                min_final_price=Decimal(str(item[5] or 0)),
                max_final_price=Decimal(str(item[6] or 0)),
            )
            for item in q.all()
        ]
