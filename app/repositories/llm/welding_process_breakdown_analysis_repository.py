"""焊接工艺拆解 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.bom.welding_process_breakdown import BomWeldingProcessBreakdownNode


def _normalize_location(location: str | None) -> str | None:
    if not location:
        return None
    text = location.strip()
    if text.endswith("基地"):
        return text[:-2]
    return text


@dataclass(frozen=True, slots=True)
class WeldingBreakdownNodeRow:
    location: str
    vehicle_model: str
    bom_version: str
    part_number: str
    part_name: str | None
    level: int
    assembly_qty: Decimal
    process_line_count: int
    parse_status: str
    audit_status: str


class WeldingProcessBreakdownAnalysisRepository:
    def query_node_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        limit: int = 5000,
    ) -> list[WeldingBreakdownNodeRow]:
        q = db.query(BomWeldingProcessBreakdownNode)
        normalized = _normalize_location(location)
        if normalized:
            q = q.filter(BomWeldingProcessBreakdownNode.location == normalized)
        if vehicle_model:
            q = q.filter(BomWeldingProcessBreakdownNode.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(BomWeldingProcessBreakdownNode.bom_version == bom_version)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(BomWeldingProcessBreakdownNode.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            BomWeldingProcessBreakdownNode.location.asc(),
            BomWeldingProcessBreakdownNode.vehicle_model.asc(),
            BomWeldingProcessBreakdownNode.bom_version.asc(),
            BomWeldingProcessBreakdownNode.part_number.asc(),
        ).limit(limit)

        return [
            WeldingBreakdownNodeRow(
                location=str(row.location),
                vehicle_model=str(row.vehicle_model),
                bom_version=str(row.bom_version),
                part_number=str(row.part_number),
                part_name=row.part_name,
                level=int(row.level),
                assembly_qty=Decimal(str(row.assembly_qty)),
                process_line_count=int(row.process_line_count or 0),
                parse_status=str(row.parse_status or "ok"),
                audit_status=str(row.audit_status or "pending"),
            )
            for row in q.all()
        ]

    def pick_best_row(
        self,
        rows: list[WeldingBreakdownNodeRow],
        *,
        part_token: str,
    ) -> WeldingBreakdownNodeRow | None:
        if not rows:
            return None
        picked = pick_part_row(
            rows,
            part_token,
            get_part_number=lambda row: row.part_number,
        )
        return picked if isinstance(picked, WeldingBreakdownNodeRow) else rows[0]
