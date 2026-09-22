"""工程变更单 — LLM 只读查询。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.engineering_change.design_change.change_order import EngineeringChangeOrder
from app.models.engineering_change.design_change.upload_log import EngineeringChangeUploadLog
from app.repositories.llm.location_in import location_in_clause


@dataclass(frozen=True, slots=True)
class EngineeringChangeRow:
    location: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    change_type: str
    before_assembly_part_number: str
    after_assembly_part_number: str | None
    assembly_name: str | None
    part_level: str
    before_part_number: str | None
    after_part_number: str | None
    part_name: str | None
    project_code: str
    status: str


def _row_part_token(row: EngineeringChangeRow) -> str:
    """优先变更后零件号，便于「新号查旧号」。"""
    return (
        (row.after_part_number or "").strip()
        or (row.before_part_number or "").strip()
        or (row.after_assembly_part_number or "").strip()
        or row.before_assembly_part_number
    )


class EngineeringChangeAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        start_year: int | None = None,
        start_month: int | None = None,
        end_year: int | None = None,
        end_month: int | None = None,
        part_number: str | None = None,
        change_types: Sequence[str] | None = None,
        limit: int = 5000,
    ) -> list[EngineeringChangeRow]:
        q = (
            db.query(EngineeringChangeOrder, EngineeringChangeUploadLog)
            .join(
                EngineeringChangeUploadLog,
                EngineeringChangeOrder.upload_log_id == EngineeringChangeUploadLog.id,
            )
            .filter(
                EngineeringChangeUploadLog.status == "success",
                EngineeringChangeOrder.status == "active",
            )
        )
        loc_filter = location_in_clause(db, EngineeringChangeUploadLog.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(EngineeringChangeUploadLog.vehicle_model == vehicle_model)
        if start_year is not None and start_month is not None:
            start_key = start_year * 12 + start_month
            q = q.filter(
                (
                    EngineeringChangeUploadLog.effective_year * 12
                    + EngineeringChangeUploadLog.effective_month
                )
                >= start_key
            )
        if end_year is not None and end_month is not None:
            end_key = end_year * 12 + end_month
            q = q.filter(
                (
                    EngineeringChangeUploadLog.effective_year * 12
                    + EngineeringChangeUploadLog.effective_month
                )
                <= end_key
            )
        if change_types:
            q = q.filter(EngineeringChangeOrder.change_type.in_(list(change_types)))
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(
                or_(
                    EngineeringChangeOrder.before_part_number.like(pattern, escape="\\"),
                    EngineeringChangeOrder.after_part_number.like(pattern, escape="\\"),
                    EngineeringChangeOrder.before_assembly_part_number.like(pattern, escape="\\"),
                    EngineeringChangeOrder.after_assembly_part_number.like(pattern, escape="\\"),
                )
            )
        q = q.order_by(
            EngineeringChangeUploadLog.effective_year.desc(),
            EngineeringChangeUploadLog.effective_month.desc(),
            EngineeringChangeOrder.excel_row.asc(),
            EngineeringChangeOrder.id.asc(),
        ).limit(limit)
        rows: list[EngineeringChangeRow] = []
        for change_order, log_row in q.all():
            rows.append(
                EngineeringChangeRow(
                    location=str(log_row.location),
                    vehicle_model=str(log_row.vehicle_model),
                    effective_year=int(log_row.effective_year),
                    effective_month=int(log_row.effective_month),
                    change_type=str(change_order.change_type),
                    before_assembly_part_number=str(change_order.before_assembly_part_number),
                    after_assembly_part_number=change_order.after_assembly_part_number,
                    assembly_name=change_order.assembly_name,
                    part_level=str(change_order.part_level),
                    before_part_number=change_order.before_part_number,
                    after_part_number=change_order.after_part_number,
                    part_name=change_order.part_name,
                    project_code=str(change_order.project_code),
                    status=str(change_order.status),
                )
            )
        return rows

    def pick_best_row(
        self,
        rows: list[EngineeringChangeRow],
        *,
        part_token: str,
    ) -> EngineeringChangeRow | None:
        if not rows:
            return None
        picked = pick_part_row(rows, part_token, get_part_number=_row_part_token)
        return picked if isinstance(picked, EngineeringChangeRow) else rows[0]
