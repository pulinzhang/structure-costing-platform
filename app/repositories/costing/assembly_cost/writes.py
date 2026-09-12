"""成品月核价写入：upsert 子行、按范围/ID 审核删除。

已审核行跳过由 Service 决定；这里只执行 SQL。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_indirect import AssemblyCostIndirect
from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.repositories.costing.assembly_cost.payloads import (
    _MAIN_FIELDS,
    AssemblyCostUpsertPayload,
)
from app.repositories.costing.assembly_cost.queries import AssemblyCostQueries


class AssemblyCostWrites:
    def __init__(self, queries: AssemblyCostQueries | None = None) -> None:
        self._queries = queries or AssemblyCostQueries()

    def upsert_with_children(
        self, db: Session, payload: AssemblyCostUpsertPayload
    ) -> tuple[AssemblyCost, bool]:
        """写入主表并替换明细；返回 (row, created)。已审核行由 Service 跳过。"""
        existing = self._queries.get_by_business_key(
            db,
            year=payload.year,
            month=payload.month,
            location=payload.location,
            vehicle_model=payload.vehicle_model,
            bom_version=payload.bom_version,
            source_node_id=payload.source_node_id,
        )
        if existing is None:
            row = AssemblyCost(
                year=payload.year,
                month=payload.month,
                location=payload.location,
                vehicle_model=payload.vehicle_model,
                bom_version=payload.bom_version,
                source_node_id=payload.source_node_id,
                part_number=payload.part_number,
                created_by=payload.created_by,
                audit_status=AUDIT_PENDING,
            )
            db.add(row)
            db.flush()
            created = True
        else:
            row = existing
            created = False
            # 先物理删除子行再插入，避免 SQLite 上 clear()+insert 同 flush 触发唯一约束冲突
            db.query(AssemblyCostItem).filter(AssemblyCostItem.assembly_cost_id == row.id).delete(
                synchronize_session=False
            )
            db.query(AssemblyCostIndirect).filter(
                AssemblyCostIndirect.assembly_cost_id == row.id
            ).delete(synchronize_session=False)
            db.expire(row, ["items", "indirects"])
            db.flush()

        for name in _MAIN_FIELDS:
            setattr(row, name, getattr(payload, name))

        for item in payload.items:
            row.items.append(
                AssemblyCostItem(
                    node_level=item.node_level,
                    bom_node_id=item.bom_node_id,
                    part_number=item.part_number,
                    part_name=item.part_name,
                    node_role=item.node_role,
                    supply_type=item.supply_type,
                    cost_source=item.cost_source,
                    match_hint=item.match_hint,
                    unit_price=item.unit_price,
                    effective_qty=item.effective_qty,
                    line_amount=item.line_amount,
                    sort_no=item.sort_no,
                )
            )
        for ind in payload.indirects:
            row.indirects.append(
                AssemblyCostIndirect(
                    code=ind.code,
                    label=ind.label,
                    amount=ind.amount,
                    rate=ind.rate,
                    base_amount=ind.base_amount,
                    sort_no=ind.sort_no,
                )
            )
        db.flush()
        return row, created

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> int:
        count = (
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.year == year,
                AssemblyCost.month == month,
                AssemblyCost.location == location,
                AssemblyCost.vehicle_model == vehicle_model,
                AssemblyCost.bom_version == bom_version,
                AssemblyCost.audit_status != AUDIT_APPROVED,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(count)

    def approve_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
    ) -> int:
        count = (
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.year == year,
                AssemblyCost.month == month,
                AssemblyCost.location == location,
                AssemblyCost.vehicle_model == vehicle_model,
                AssemblyCost.bom_version == bom_version,
                AssemblyCost.audit_status != AUDIT_APPROVED,
            )
            .update(
                {
                    AssemblyCost.audit_status: AUDIT_APPROVED,
                    AssemblyCost.audited_by: audited_by,
                    AssemblyCost.audited_at: audited_at,
                    AssemblyCost.audit_remark: audit_remark,
                },
                synchronize_session=False,
            )
        )
        db.flush()
        return int(count)

    def reverse_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str | None,
    ) -> int:
        count = (
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.year == year,
                AssemblyCost.month == month,
                AssemblyCost.location == location,
                AssemblyCost.vehicle_model == vehicle_model,
                AssemblyCost.bom_version == bom_version,
                AssemblyCost.audit_status == AUDIT_APPROVED,
            )
            .update(
                {
                    AssemblyCost.audit_status: AUDIT_PENDING,
                    AssemblyCost.reverse_audited_by: reverse_audited_by,
                    AssemblyCost.reverse_audited_at: reverse_audited_at,
                    AssemblyCost.reverse_audit_remark: reverse_audit_remark,
                },
                synchronize_session=False,
            )
        )
        db.flush()
        return int(count)

    def delete_by_ids(self, db: Session, ids: list[int]) -> int:
        if not ids:
            return 0
        count = (
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.id.in_(ids),
                AssemblyCost.audit_status != AUDIT_APPROVED,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(count)

    def approve_by_ids(
        self,
        db: Session,
        ids: list[int],
        *,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
    ) -> int:
        if not ids:
            return 0
        count = (
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.id.in_(ids),
                AssemblyCost.audit_status != AUDIT_APPROVED,
            )
            .update(
                {
                    AssemblyCost.audit_status: AUDIT_APPROVED,
                    AssemblyCost.audited_by: audited_by,
                    AssemblyCost.audited_at: audited_at,
                    AssemblyCost.audit_remark: audit_remark,
                },
                synchronize_session=False,
            )
        )
        db.flush()
        return int(count)

    def reverse_by_ids(
        self,
        db: Session,
        ids: list[int],
        *,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str | None,
    ) -> int:
        if not ids:
            return 0
        count = (
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.id.in_(ids),
                AssemblyCost.audit_status == AUDIT_APPROVED,
            )
            .update(
                {
                    AssemblyCost.audit_status: AUDIT_PENDING,
                    AssemblyCost.reverse_audited_by: reverse_audited_by,
                    AssemblyCost.reverse_audited_at: reverse_audited_at,
                    AssemblyCost.reverse_audit_remark: reverse_audit_remark,
                },
                synchronize_session=False,
            )
        )
        db.flush()
        return int(count)
