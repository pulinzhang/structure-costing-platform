"""采购对象列表 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.bom.procurement_object import BomProcurementObject, BomProcurementObjectList
from app.repositories.llm.location_in import location_in_clause


@dataclass(frozen=True, slots=True)
class ProcurementObjectRow:
    location: str
    vehicle_model: str
    bom_version: str
    part_number: str
    part_name: str | None
    section: str
    object_kind: str | None
    confirm_status: str
    audit_status: str
    supplier_name: str | None


class ProcurementObjectAnalysisRepository:
    def query_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        limit: int = 5000,
    ) -> list[ProcurementObjectRow]:
        q = db.query(BomProcurementObject, BomProcurementObjectList).join(
            BomProcurementObjectList,
            BomProcurementObject.list_id == BomProcurementObjectList.id,
        )
        loc_filter = location_in_clause(db, BomProcurementObjectList.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(BomProcurementObjectList.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(BomProcurementObjectList.bom_version == bom_version)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(BomProcurementObject.part_number.like(pattern, escape="\\"))
        q = q.order_by(
            BomProcurementObjectList.generated_at.desc(),
            BomProcurementObject.part_number.asc(),
        ).limit(limit)
        rows: list[ProcurementObjectRow] = []
        for obj, header in q.all():
            rows.append(
                ProcurementObjectRow(
                    location=str(header.location),
                    vehicle_model=str(header.vehicle_model),
                    bom_version=str(header.bom_version),
                    part_number=str(obj.part_number),
                    part_name=obj.part_name,
                    section=str(obj.section),
                    object_kind=obj.object_kind,
                    confirm_status=str(obj.confirm_status or "pending"),
                    audit_status=str(obj.audit_status or "pending"),
                    supplier_name=obj.supplier_name,
                )
            )
        return rows

    def pick_best_row(
        self,
        rows: list[ProcurementObjectRow],
        *,
        part_token: str,
    ) -> ProcurementObjectRow | None:
        if not rows:
            return None
        picked = pick_part_row(rows, part_token, get_part_number=lambda row: row.part_number)
        return picked if isinstance(picked, ProcurementObjectRow) else rows[0]
