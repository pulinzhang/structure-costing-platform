"""焊接单价 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bom.welding_unit_price import BomWeldingUnitPrice


def _normalize_location(location: str | None) -> str | None:
    if not location:
        return None
    text = location.strip()
    if text.endswith("基地"):
        return text[:-2]
    return text


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
        normalized = _normalize_location(location)
        if normalized:
            q = q.filter(BomWeldingUnitPrice.location == normalized)
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
