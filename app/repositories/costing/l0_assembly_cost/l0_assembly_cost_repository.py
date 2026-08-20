"""成品月核价 — Repository。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TypeVar, TypedDict

from sqlalchemy import case, func
from sqlalchemy.orm import Query, Session, joinedload, noload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.costing.l0_assembly_cost import L0AssemblyCost
from app.models.costing.l0_assembly_cost_indirect import L0AssemblyCostIndirect
from app.models.costing.l0_assembly_cost_item import L0AssemblyCostItem

_T = TypeVar("_T")


@dataclass(frozen=True)
class L0AssemblyCostItemInsert:
    level_label: str
    bom_node_id: int | None
    part_number: str
    part_name: str | None
    node_role: str | None
    supply_type: str | None
    cost_source: str
    match_hint: str | None
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal
    sort_no: int


@dataclass(frozen=True)
class L0AssemblyCostIndirectInsert:
    code: str
    label: str
    amount: Decimal
    rate: Decimal | None
    base_amount: Decimal | None
    sort_no: int


@dataclass
class L0AssemblyCostUpsertPayload:
    year: int
    month: int
    location: str
    vehicle_model: str
    bom_version: str
    part_number: str
    part_name: str | None
    supply_qty: Decimal
    bom_snapshot_id: int | None
    sketch_url: str | None
    stamping_amount: Decimal
    purchased_amount: Decimal
    bundle_amount: Decimal
    material_amount: Decimal
    welding_amount: Decimal
    welding_other_fee: Decimal
    total_amount: Decimal
    unit_transport_fee: Decimal
    warehouse_bundling_fee: Decimal
    finished_finance_fee: Decimal
    finished_management_fee: Decimal
    finished_scrap_fee: Decimal
    finished_pretax_profit_fee: Decimal
    gauge_alloc_fee: Decimal
    fixture_alloc_fee: Decimal
    allocation_fee_total: Decimal
    indirect_amount: Decimal
    grand_total: Decimal
    finance_rate: Decimal
    management_rate: Decimal
    scrap_rate: Decimal
    pretax_profit_rate: Decimal
    welding_fee_id: int | None
    welding_summary: str | None
    calc_status: str
    missing_leaf_count: int
    calc_message: str | None
    formula_version: str | None
    calculated_at: datetime | None
    calc_batch_id: str | None
    created_by: str
    updated_by: str
    items: list[L0AssemblyCostItemInsert]
    indirects: list[L0AssemblyCostIndirectInsert]


class L0AssemblyCostFilterSummary(TypedDict):
    total_count: int
    ok_count: int
    partial_count: int
    pending_count: int
    approved_count: int
    grand_total_sum: Decimal
    total_amount_sum: Decimal


class L0AssemblyCostListFilters(TypedDict):
    year: int | None
    month: int | None
    location: str | None
    vehicle_model: str | None
    bom_version: str | None
    part_number: str | None
    audit_status: str | None
    calc_status: str | None
    summary: L0AssemblyCostFilterSummary


_MAIN_FIELDS = (
    "part_name",
    "supply_qty",
    "bom_snapshot_id",
    "sketch_url",
    "stamping_amount",
    "purchased_amount",
    "bundle_amount",
    "material_amount",
    "welding_amount",
    "welding_other_fee",
    "total_amount",
    "unit_transport_fee",
    "warehouse_bundling_fee",
    "finished_finance_fee",
    "finished_management_fee",
    "finished_scrap_fee",
    "finished_pretax_profit_fee",
    "gauge_alloc_fee",
    "fixture_alloc_fee",
    "allocation_fee_total",
    "indirect_amount",
    "grand_total",
    "finance_rate",
    "management_rate",
    "scrap_rate",
    "pretax_profit_rate",
    "welding_fee_id",
    "welding_summary",
    "calc_status",
    "missing_leaf_count",
    "calc_message",
    "formula_version",
    "calculated_at",
    "calc_batch_id",
    "updated_by",
)


class L0AssemblyCostRepository:
    """成品月核价结果数据访问。"""

    def get_by_id(self, db: Session, cost_id: int) -> L0AssemblyCost | None:
        return (
            db.query(L0AssemblyCost)
            .options(
                joinedload(L0AssemblyCost.items),
                joinedload(L0AssemblyCost.indirects),
            )
            .filter(L0AssemblyCost.id == cost_id)
            .first()
        )

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        part_number: str,
    ) -> L0AssemblyCost | None:
        return (
            db.query(L0AssemblyCost)
            .filter(
                L0AssemblyCost.year == year,
                L0AssemblyCost.month == month,
                L0AssemblyCost.location == location,
                L0AssemblyCost.vehicle_model == vehicle_model,
                L0AssemblyCost.bom_version == bom_version,
                L0AssemblyCost.part_number == part_number,
            )
            .first()
        )

    def upsert_with_children(
        self, db: Session, payload: L0AssemblyCostUpsertPayload
    ) -> tuple[L0AssemblyCost, bool]:
        """写入主表并替换明细；返回 (row, created)。已审核行由 Service 跳过。"""
        existing = self.get_by_business_key(
            db,
            year=payload.year,
            month=payload.month,
            location=payload.location,
            vehicle_model=payload.vehicle_model,
            bom_version=payload.bom_version,
            part_number=payload.part_number,
        )
        if existing is None:
            row = L0AssemblyCost(
                year=payload.year,
                month=payload.month,
                location=payload.location,
                vehicle_model=payload.vehicle_model,
                bom_version=payload.bom_version,
                part_number=payload.part_number,
                created_by=payload.created_by,
                audit_status=AUDIT_PENDING,
            )
            db.add(row)
            created = True
        else:
            row = existing
            created = False
            row.items.clear()
            row.indirects.clear()

        for name in _MAIN_FIELDS:
            setattr(row, name, getattr(payload, name))

        for item in payload.items:
            row.items.append(
                L0AssemblyCostItem(
                    level_label=item.level_label,
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
                L0AssemblyCostIndirect(
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

    def _apply_filters(
        self,
        q: Query[_T],
        *,
        year: int | None,
        month: int | None,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        part_number: str | None,
        audit_status: str | None,
        calc_status: str | None,
    ) -> Query[_T]:
        if year is not None:
            q = q.filter(L0AssemblyCost.year == year)
        if month is not None:
            q = q.filter(L0AssemblyCost.month == month)
        if location:
            q = q.filter(L0AssemblyCost.location == location)
        if vehicle_model:
            q = q.filter(L0AssemblyCost.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(L0AssemblyCost.bom_version == bom_version)
        if part_number:
            q = q.filter(L0AssemblyCost.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(L0AssemblyCost.audit_status == audit_status)
        if calc_status:
            q = q.filter(L0AssemblyCost.calc_status == calc_status)
        return q

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[L0AssemblyCost], int, L0AssemblyCostListFilters]:
        q = db.query(L0AssemblyCost)
        q = self._apply_filters(
            q,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
        )
        total = q.count()
        rows = (
            q.options(
                noload(L0AssemblyCost.items),
                noload(L0AssemblyCost.indirects),
            )
            .order_by(
                L0AssemblyCost.id.asc()
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        agg = (
            self._apply_filters(
                db.query(
                    func.count(L0AssemblyCost.id),
                    func.coalesce(
                        func.sum(
                            case(
                                (L0AssemblyCost.calc_status == "ok", 1),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case(
                                (L0AssemblyCost.calc_status == "partial", 1),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case(
                                (L0AssemblyCost.audit_status == AUDIT_PENDING, 1),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case(
                                (L0AssemblyCost.audit_status == AUDIT_APPROVED, 1),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                    func.coalesce(func.sum(L0AssemblyCost.grand_total), 0),
                    func.coalesce(func.sum(L0AssemblyCost.total_amount), 0),
                ),
                year=year,
                month=month,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                part_number=part_number,
                audit_status=audit_status,
                calc_status=calc_status,
            ).one()
        )
        summary: L0AssemblyCostFilterSummary = {
            "total_count": int(agg[0] or 0),
            "ok_count": int(agg[1] or 0),
            "partial_count": int(agg[2] or 0),
            "pending_count": int(agg[3] or 0),
            "approved_count": int(agg[4] or 0),
            "grand_total_sum": Decimal(str(agg[5] or 0)),
            "total_amount_sum": Decimal(str(agg[6] or 0)),
        }
        filters: L0AssemblyCostListFilters = {
            "year": year,
            "month": month,
            "location": location,
            "vehicle_model": vehicle_model,
            "bom_version": bom_version,
            "part_number": part_number,
            "audit_status": audit_status,
            "calc_status": calc_status,
            "summary": summary,
        }
        return rows, total, filters

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
    ) -> list[L0AssemblyCost]:
        """按筛选导出：主表 + items + indirects。"""
        q = db.query(L0AssemblyCost)
        q = self._apply_filters(
            q,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
        )
        return (
            q.options(
                joinedload(L0AssemblyCost.items),
                joinedload(L0AssemblyCost.indirects),
            )
            .order_by(
                L0AssemblyCost.year.desc(),
                L0AssemblyCost.month.desc(),
                L0AssemblyCost.location,
                L0AssemblyCost.vehicle_model,
                L0AssemblyCost.bom_version,
                L0AssemblyCost.part_number,
                L0AssemblyCost.id.asc(),
            )
            .all()
        )

    def list_ids_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        only_pending: bool = False,
    ) -> list[int]:
        q = db.query(L0AssemblyCost.id).filter(
            L0AssemblyCost.year == year,
            L0AssemblyCost.month == month,
            L0AssemblyCost.location == location,
            L0AssemblyCost.vehicle_model == vehicle_model,
            L0AssemblyCost.bom_version == bom_version,
        )
        if only_pending:
            q = q.filter(L0AssemblyCost.audit_status == AUDIT_PENDING)
        return [row[0] for row in q.all()]

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
            db.query(L0AssemblyCost)
            .filter(
                L0AssemblyCost.year == year,
                L0AssemblyCost.month == month,
                L0AssemblyCost.location == location,
                L0AssemblyCost.vehicle_model == vehicle_model,
                L0AssemblyCost.bom_version == bom_version,
                L0AssemblyCost.audit_status != AUDIT_APPROVED,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(count)

    def count_approved_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> int:
        return (
            db.query(L0AssemblyCost)
            .filter(
                L0AssemblyCost.year == year,
                L0AssemblyCost.month == month,
                L0AssemblyCost.location == location,
                L0AssemblyCost.vehicle_model == vehicle_model,
                L0AssemblyCost.bom_version == bom_version,
                L0AssemblyCost.audit_status == AUDIT_APPROVED,
            )
            .count()
        )

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
            db.query(L0AssemblyCost)
            .filter(
                L0AssemblyCost.year == year,
                L0AssemblyCost.month == month,
                L0AssemblyCost.location == location,
                L0AssemblyCost.vehicle_model == vehicle_model,
                L0AssemblyCost.bom_version == bom_version,
                L0AssemblyCost.audit_status != AUDIT_APPROVED,
            )
            .update(
                {
                    L0AssemblyCost.audit_status: AUDIT_APPROVED,
                    L0AssemblyCost.audited_by: audited_by,
                    L0AssemblyCost.audited_at: audited_at,
                    L0AssemblyCost.audit_remark: audit_remark,
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
            db.query(L0AssemblyCost)
            .filter(
                L0AssemblyCost.year == year,
                L0AssemblyCost.month == month,
                L0AssemblyCost.location == location,
                L0AssemblyCost.vehicle_model == vehicle_model,
                L0AssemblyCost.bom_version == bom_version,
                L0AssemblyCost.audit_status == AUDIT_APPROVED,
            )
            .update(
                {
                    L0AssemblyCost.audit_status: AUDIT_PENDING,
                    L0AssemblyCost.reverse_audited_by: reverse_audited_by,
                    L0AssemblyCost.reverse_audited_at: reverse_audited_at,
                    L0AssemblyCost.reverse_audit_remark: reverse_audit_remark,
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
            db.query(L0AssemblyCost)
            .filter(
                L0AssemblyCost.id.in_(ids),
                L0AssemblyCost.audit_status != AUDIT_APPROVED,
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
            db.query(L0AssemblyCost)
            .filter(
                L0AssemblyCost.id.in_(ids),
                L0AssemblyCost.audit_status != AUDIT_APPROVED,
            )
            .update(
                {
                    L0AssemblyCost.audit_status: AUDIT_APPROVED,
                    L0AssemblyCost.audited_by: audited_by,
                    L0AssemblyCost.audited_at: audited_at,
                    L0AssemblyCost.audit_remark: audit_remark,
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
            db.query(L0AssemblyCost)
            .filter(
                L0AssemblyCost.id.in_(ids),
                L0AssemblyCost.audit_status == AUDIT_APPROVED,
            )
            .update(
                {
                    L0AssemblyCost.audit_status: AUDIT_PENDING,
                    L0AssemblyCost.reverse_audited_by: reverse_audited_by,
                    L0AssemblyCost.reverse_audited_at: reverse_audited_at,
                    L0AssemblyCost.reverse_audit_remark: reverse_audit_remark,
                },
                synchronize_session=False,
            )
        )
        db.flush()
        return int(count)

    def list_distinct_years(self, db: Session) -> list[int]:
        rows = (
            db.query(L0AssemblyCost.year)
            .distinct()
            .order_by(L0AssemblyCost.year.desc())
            .all()
        )
        return [int(r[0]) for r in rows]
