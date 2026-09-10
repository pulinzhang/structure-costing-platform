"""冲压模具费 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.stamping.die_fee import StampingDieFee
from app.repositories.llm.location_in import location_in_clause


@dataclass(frozen=True, slots=True)
class DieFeeRow:
    year: int
    location: str
    vehicle_model: str
    part_number: str
    part_name: str | None
    final_die_fee: Decimal
    die_fee: Decimal
    audit_status: str


class DieFeeAnalysisRepository:
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
    ) -> list[DieFeeRow]:
        q = db.query(StampingDieFee)
        loc_filter = location_in_clause(db, StampingDieFee.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(StampingDieFee.vehicle_model == vehicle_model)
        if start_year is not None:
            q = q.filter(StampingDieFee.year >= start_year)
        if end_year is not None:
            q = q.filter(StampingDieFee.year <= end_year)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(StampingDieFee.part_number.like(pattern, escape="\\"))
        q = q.order_by(
            StampingDieFee.year.desc(),
            StampingDieFee.part_number.asc(),
        ).limit(limit)
        return [
            DieFeeRow(
                year=int(row.year),
                location=str(row.location),
                vehicle_model=str(row.vehicle_model),
                part_number=str(row.part_number),
                part_name=row.part_name,
                final_die_fee=Decimal(str(row.final_die_fee or 0)),
                die_fee=Decimal(str(row.die_fee or 0)),
                audit_status=str(row.audit_status or "pending"),
            )
            for row in q.all()
        ]

    def pick_best_row(self, rows: list[DieFeeRow], *, part_token: str) -> DieFeeRow | None:
        if not rows:
            return None
        picked = pick_part_row(rows, part_token, get_part_number=lambda row: row.part_number)
        return picked if isinstance(picked, DieFeeRow) else rows[0]
