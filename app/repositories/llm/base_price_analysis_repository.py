"""基准价格 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.yishiyiyi import SteelBasePrice
from app.repositories.llm.location_in import location_in_clause
from app.services.llm._money import ym_int


@dataclass(frozen=True, slots=True)
class BasePricePeriodRow:
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    spec: str
    base_price: Decimal
    processing_fee: Decimal
    thick: Decimal | None = None
    width: Decimal | None = None


class BasePriceAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        location: str | None = None,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        limit: int = 8000,
    ) -> list[BasePricePeriodRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = SteelBasePrice.year * 100 + SteelBasePrice.month

        q = db.query(SteelBasePrice).filter(ym_expr >= start, ym_expr <= end)
        loc_filter = location_in_clause(db, SteelBasePrice.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if steel_mill:
            q = q.filter(SteelBasePrice.steel_mill == steel_mill)
        if category_name:
            q = q.filter(SteelBasePrice.category_name == category_name)
        if grade:
            q = q.filter(SteelBasePrice.grade.contains(grade))

        q = q.order_by(
            SteelBasePrice.year.asc(),
            SteelBasePrice.month.asc(),
            SteelBasePrice.location.asc(),
            SteelBasePrice.steel_mill.asc(),
        ).limit(limit)

        rows: list[BasePricePeriodRow] = []
        for row in q.all():
            rows.append(
                BasePricePeriodRow(
                    year=int(row.year),
                    month=int(row.month),
                    location=str(row.location),
                    steel_mill=str(row.steel_mill),
                    category_name=str(row.category_name),
                    grade=str(row.grade),
                    spec=str(row.spec),
                    base_price=Decimal(str(row.base_price)),
                    processing_fee=Decimal(str(row.processing_fee)),
                    thick=Decimal(str(row.thick)),
                    width=Decimal(str(row.width)),
                )
            )
        return rows
