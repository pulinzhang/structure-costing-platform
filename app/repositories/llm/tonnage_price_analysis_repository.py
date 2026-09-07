"""冲次单价 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.stamping import StampingTonnagePrice
from app.repositories.llm.location_in import location_in_clause


@dataclass(frozen=True, slots=True)
class TonnagePriceRow:
    location: str
    year: int
    tonnage: int
    price_per_stroke: Decimal
    audit_status: str


class TonnagePriceAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        year: int | None = None,
        tonnage: int | None = None,
        limit: int = 500,
    ) -> list[TonnagePriceRow]:
        q = db.query(StampingTonnagePrice)
        loc_filter = location_in_clause(db, StampingTonnagePrice.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if year is not None:
            q = q.filter(StampingTonnagePrice.year == year)
        if tonnage is not None:
            q = q.filter(StampingTonnagePrice.tonnage == tonnage)

        q = q.order_by(
            StampingTonnagePrice.location.asc(),
            StampingTonnagePrice.year.desc(),
            StampingTonnagePrice.tonnage.asc(),
        ).limit(limit)

        return [
            TonnagePriceRow(
                location=str(row.location),
                year=int(row.year),
                tonnage=int(row.tonnage),
                price_per_stroke=Decimal(str(row.price_per_stroke)),
                audit_status=str(row.audit_status or "pending"),
            )
            for row in q.all()
        ]
