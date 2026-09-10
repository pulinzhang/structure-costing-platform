"""检具费档案 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.stamping.gauge_fee import StampingGaugeFee
from app.repositories.llm.location_in import location_in_clause


@dataclass(frozen=True, slots=True)
class GaugeFeeRow:
    location: str
    vehicle_model: str
    part_number: str
    part_name: str | None
    gauge_fee: Decimal
    allocation_qty: Decimal
    status: str


class GaugeFeeAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        part_number: str | None = None,
        limit: int = 5000,
    ) -> list[GaugeFeeRow]:
        q = db.query(StampingGaugeFee)
        loc_filter = location_in_clause(db, StampingGaugeFee.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(StampingGaugeFee.vehicle_model == vehicle_model)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(StampingGaugeFee.part_number.like(pattern, escape="\\"))
        q = q.order_by(StampingGaugeFee.part_number.asc()).limit(limit)
        return [
            GaugeFeeRow(
                location=str(row.location),
                vehicle_model=str(row.vehicle_model),
                part_number=str(row.part_number),
                part_name=row.part_name,
                gauge_fee=Decimal(str(row.gauge_fee or 0)),
                allocation_qty=Decimal(str(row.allocation_qty or 0)),
                status=str(row.status or "effective"),
            )
            for row in q.all()
        ]

    def pick_best_row(self, rows: list[GaugeFeeRow], *, part_token: str) -> GaugeFeeRow | None:
        if not rows:
            return None
        picked = pick_part_row(rows, part_token, get_part_number=lambda row: row.part_number)
        return picked if isinstance(picked, GaugeFeeRow) else rows[0]
