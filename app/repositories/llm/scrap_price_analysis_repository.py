"""废料月度销售价 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.yishiyiyi import StampingScrapPrice
from app.services.llm._money import ym_int


@dataclass(frozen=True, slots=True)
class ScrapPricePeriodRow:
    year: int
    month: int
    location: str
    market_price: Decimal
    deduction_fee: Decimal
    net_price: Decimal


def _normalize_scrap_location(location: str | None) -> str | None:
    if not location:
        return None
    text = location.strip()
    if text.endswith("基地"):
        return text[:-2]
    return text


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

        q = db.query(StampingScrapPrice).filter(ym_expr >= start, ym_expr <= end)
        normalized = _normalize_scrap_location(location)
        if normalized:
            q = q.filter(StampingScrapPrice.location == normalized)

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
