"""年度零件价 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.bom.annual_part_price import BomAnnualPartPrice


def _normalize_location(location: str | None) -> str | None:
    if not location:
        return None
    text = location.strip()
    if text.endswith("基地"):
        return text[:-2]
    return text


@dataclass(frozen=True, slots=True)
class AnnualPartPriceRow:
    year: int
    location: str
    part_number: str
    part_name: str | None
    unit: str
    unit_price: Decimal
    supply_type: str
    audit_status: str


class AnnualPartPriceAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        part_number: str | None = None,
        limit: int = 5000,
    ) -> list[AnnualPartPriceRow]:
        q = db.query(BomAnnualPartPrice)
        normalized = _normalize_location(location)
        if normalized:
            q = q.filter(BomAnnualPartPrice.location == normalized)
        if start_year is not None:
            q = q.filter(BomAnnualPartPrice.year >= start_year)
        if end_year is not None:
            q = q.filter(BomAnnualPartPrice.year <= end_year)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(BomAnnualPartPrice.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            BomAnnualPartPrice.year.asc(),
            BomAnnualPartPrice.location.asc(),
            BomAnnualPartPrice.part_number.asc(),
        ).limit(limit)

        return [
            AnnualPartPriceRow(
                year=int(row.year),
                location=str(row.location),
                part_number=str(row.part_number),
                part_name=row.part_name,
                unit=str(row.unit),
                unit_price=Decimal(str(row.unit_price)),
                supply_type=str(row.supply_type),
                audit_status=str(row.audit_status or "pending"),
            )
            for row in q.all()
        ]

    def pick_best_row(
        self,
        rows: list[AnnualPartPriceRow],
        *,
        part_token: str,
    ) -> AnnualPartPriceRow | None:
        if not rows:
            return None
        picked = pick_part_row(
            rows,
            part_token,
            get_part_number=lambda row: row.part_number,
        )
        return picked if isinstance(picked, AnnualPartPriceRow) else rows[0]
