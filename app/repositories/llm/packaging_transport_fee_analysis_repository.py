"""包装运输费 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.bom.packaging_transport_fee import BomPackagingTransportFee


def _normalize_location(location: str | None) -> str | None:
    if not location:
        return None
    text = location.strip()
    if text.endswith("基地"):
        return text[:-2]
    return text


@dataclass(frozen=True, slots=True)
class PackagingTransportFeeRow:
    year: int
    location: str
    vehicle_model: str
    part_number: str
    part_name: str | None
    unit_packaging_fee: Decimal
    unit_transport_fee: Decimal
    packaging_transport_total: Decimal
    audit_status: str


class PackagingTransportFeeAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        part_number: str | None = None,
        limit: int = 5000,
    ) -> list[PackagingTransportFeeRow]:
        q = db.query(BomPackagingTransportFee)
        normalized = _normalize_location(location)
        if normalized:
            q = q.filter(BomPackagingTransportFee.location == normalized)
        if vehicle_model:
            q = q.filter(BomPackagingTransportFee.vehicle_model == vehicle_model)
        if start_year is not None:
            q = q.filter(BomPackagingTransportFee.year >= start_year)
        if end_year is not None:
            q = q.filter(BomPackagingTransportFee.year <= end_year)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(BomPackagingTransportFee.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            BomPackagingTransportFee.year.asc(),
            BomPackagingTransportFee.location.asc(),
            BomPackagingTransportFee.vehicle_model.asc(),
            BomPackagingTransportFee.part_number.asc(),
        ).limit(limit)

        return [
            PackagingTransportFeeRow(
                year=int(row.year),
                location=str(row.location),
                vehicle_model=str(row.vehicle_model),
                part_number=str(row.part_number),
                part_name=row.part_name,
                unit_packaging_fee=Decimal(str(row.unit_packaging_fee)),
                unit_transport_fee=Decimal(str(row.unit_transport_fee)),
                packaging_transport_total=Decimal(str(row.packaging_transport_total)),
                audit_status=str(row.audit_status or "pending"),
            )
            for row in q.all()
        ]

    def pick_best_row(
        self,
        rows: list[PackagingTransportFeeRow],
        *,
        part_token: str,
    ) -> PackagingTransportFeeRow | None:
        if not rows:
            return None
        picked = pick_part_row(
            rows,
            part_token,
            get_part_number=lambda row: row.part_number,
        )
        return picked if isinstance(picked, PackagingTransportFeeRow) else rows[0]
