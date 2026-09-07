"""焊接单价 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bom.welding_unit_price import BomWeldingUnitPrice
from app.repositories.llm.location_in import location_in_clause


@dataclass(frozen=True, slots=True)
class WeldingUnitPriceRow:
    year: int
    location: str
    item_name: str
    unit: str
    unit_price: Decimal
    audit_status: str


class WeldingUnitPriceAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        item_name: str | None = None,
        limit: int = 5000,
    ) -> list[WeldingUnitPriceRow]:
        q = db.query(BomWeldingUnitPrice)
        loc_filter = location_in_clause(db, BomWeldingUnitPrice.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if start_year is not None:
            q = q.filter(BomWeldingUnitPrice.year >= start_year)
        if end_year is not None:
            q = q.filter(BomWeldingUnitPrice.year <= end_year)
        if item_name:
            pattern = f"%{item_name.strip()}%"
            q = q.filter(BomWeldingUnitPrice.item_name.like(pattern))

        q = q.order_by(
            BomWeldingUnitPrice.year.asc(),
            BomWeldingUnitPrice.location.asc(),
            BomWeldingUnitPrice.item_name.asc(),
        ).limit(limit)

        return [
            WeldingUnitPriceRow(
                year=int(row.year),
                location=str(row.location),
                item_name=str(row.item_name),
                unit=str(row.unit),
                unit_price=Decimal(str(row.unit_price)),
                audit_status=str(row.audit_status or "pending"),
            )
            for row in q.all()
        ]
