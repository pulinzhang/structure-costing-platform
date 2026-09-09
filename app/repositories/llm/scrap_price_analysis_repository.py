"""废料月度销售价 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.scrap_categories import SCRAP_CATEGORY_STEEL
from app.models.yishiyiyi import StampingScrapPrice
from app.repositories.llm.location_in import location_in_or_exact_clause
from app.services.llm._money import ym_int


@dataclass(frozen=True, slots=True)
class ScrapPricePeriodRow:
    year: int
    month: int
    location: str
    market_price: Decimal
    deduction_fee: Decimal
    net_price: Decimal


class ScrapPriceAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        location: str | None = None,
        limit: int = 500,
    ) -> list[ScrapPricePeriodRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = StampingScrapPrice.year * 100 + StampingScrapPrice.month

        q = db.query(StampingScrapPrice).filter(
            ym_expr >= start,
            ym_expr <= end,
            StampingScrapPrice.scrap_category == SCRAP_CATEGORY_STEEL,
        )
        loc_filter = location_in_or_exact_clause(db, StampingScrapPrice.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)

        q = q.order_by(
            StampingScrapPrice.year.asc(),
            StampingScrapPrice.month.asc(),
            StampingScrapPrice.location.asc(),
        ).limit(limit)

        rows: list[ScrapPricePeriodRow] = []
        for row in q.all():
            rows.append(
                ScrapPricePeriodRow(
                    year=int(row.year),
                    month=int(row.month),
                    location=str(row.location),
                    market_price=Decimal(str(row.market_price)),
                    deduction_fee=Decimal(str(row.deduction_fee)),
                    net_price=Decimal(str(row.net_price)),
                )
            )
        return rows
