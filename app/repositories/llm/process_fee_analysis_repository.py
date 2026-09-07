"""冲压加工费 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.stamping import StampingProcessFee
from app.repositories.llm.location_in import location_in_clause


@dataclass(frozen=True, slots=True)
class ProcessFeeRow:
    year: int
    location: str
    stamping_supplier: str
    vehicle_model: str
    version: str
    part_number: str
    part_name: str | None
    processing_fee: Decimal | None
    other_fee: Decimal | None
    final_processing_fee: Decimal | None
    process_count: int
    audit_status: str


class ProcessFeeAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        stamping_supplier: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        part_number: str | None = None,
        limit: int = 5000,
    ) -> list[ProcessFeeRow]:
        q = db.query(StampingProcessFee)
        loc_filter = location_in_clause(db, StampingProcessFee.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(StampingProcessFee.vehicle_model == vehicle_model)
        if version:
            q = q.filter(StampingProcessFee.version == version)
        if stamping_supplier:
            q = q.filter(StampingProcessFee.stamping_supplier == stamping_supplier)
        if start_year is not None:
            q = q.filter(StampingProcessFee.year >= start_year)
        if end_year is not None:
            q = q.filter(StampingProcessFee.year <= end_year)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(StampingProcessFee.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            StampingProcessFee.year.desc(),
            StampingProcessFee.location.asc(),
            StampingProcessFee.part_number.asc(),
        ).limit(limit)

        return [
            ProcessFeeRow(
                year=int(row.year),
                location=str(row.location),
                stamping_supplier=str(row.stamping_supplier),
                vehicle_model=str(row.vehicle_model),
                version=str(row.version),
                part_number=str(row.part_number),
                part_name=row.part_name,
                processing_fee=(
                    Decimal(str(row.processing_fee)) if row.processing_fee is not None else None
                ),
                other_fee=(Decimal(str(row.other_fee)) if row.other_fee is not None else None),
                final_processing_fee=(
                    Decimal(str(row.final_processing_fee))
                    if row.final_processing_fee is not None
                    else None
                ),
                process_count=int(row.process_count or 0),
                audit_status=str(row.audit_status or "pending"),
            )
            for row in q.all()
        ]

    def pick_best_row(
        self,
        rows: list[ProcessFeeRow],
        *,
        part_token: str,
    ) -> ProcessFeeRow | None:
        if not rows:
            return None
        picked = pick_part_row(
            rows,
            part_token,
            get_part_number=lambda row: row.part_number,
        )
        return picked if isinstance(picked, ProcessFeeRow) else rows[0]
