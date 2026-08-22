"""成品焊接费 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.bom.l0_welding_fee import BomL0WeldingFee


def _normalize_location(location: str | None) -> str | None:
    if not location:
        return None
    text = location.strip()
    if text.endswith("基地"):
        return text[:-2]
    return text


@dataclass(frozen=True, slots=True)
class L0WeldingFeeRow:
    year: int
    location: str
    vehicle_model: str
    bom_version: str
    part_number: str
    part_name: str | None
    total_l0_welding_fee: Decimal
    other_fee: Decimal | None
    final_l0_welding_fee: Decimal | None
    calc_status: str
    audit_status: str


class L0WeldingFeeAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        part_number: str | None = None,
        limit: int = 5000,
    ) -> list[L0WeldingFeeRow]:
        q = db.query(BomL0WeldingFee)
        normalized = _normalize_location(location)
        if normalized:
            q = q.filter(BomL0WeldingFee.location == normalized)
        if vehicle_model:
            q = q.filter(BomL0WeldingFee.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(BomL0WeldingFee.bom_version == bom_version)
        if start_year is not None:
            q = q.filter(BomL0WeldingFee.year >= start_year)
        if end_year is not None:
            q = q.filter(BomL0WeldingFee.year <= end_year)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(BomL0WeldingFee.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            BomL0WeldingFee.year.asc(),
            BomL0WeldingFee.location.asc(),
            BomL0WeldingFee.part_number.asc(),
        ).limit(limit)

        return [
            L0WeldingFeeRow(
                year=int(row.year),
                location=str(row.location),
                vehicle_model=str(row.vehicle_model),
                bom_version=str(row.bom_version),
                part_number=str(row.part_number),
                part_name=row.part_name,
                total_l0_welding_fee=Decimal(str(row.total_l0_welding_fee or 0)),
                other_fee=(
                    Decimal(str(row.other_fee)) if row.other_fee is not None else None
                ),
                final_l0_welding_fee=(
                    Decimal(str(row.final_l0_welding_fee))
                    if row.final_l0_welding_fee is not None
                    else None
                ),
                calc_status=str(row.calc_status or "ok"),
                audit_status=str(row.audit_status or "pending"),
            )
            for row in q.all()
        ]

    def pick_best_row(
        self,
        rows: list[L0WeldingFeeRow],
        *,
        part_token: str,
    ) -> L0WeldingFeeRow | None:
        if not rows:
            return None
        picked = pick_part_row(
            rows,
            part_token,
            get_part_number=lambda row: row.part_number,
        )
        return picked if isinstance(picked, L0WeldingFeeRow) else rows[0]
