"""成品月核价 — Repository。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, TypedDict, TypeVar

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Query, Session, joinedload, noload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom.node import BomNode
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_indirect import AssemblyCostIndirect
from app.models.costing.assembly_cost_item import AssemblyCostItem

_T = TypeVar("_T")
_IN_CHUNK = 400
SettlementAmountField = Literal["total_amount", "grand_total"]
_SETTLEMENT_AMOUNT_COLUMNS = {
    "total_amount": AssemblyCost.total_amount,
    "grand_total": AssemblyCost.grand_total,
}


def _chunks(values: list[int]) -> list[list[int]]:
    if not values:
        return []
    return [values[index : index + _IN_CHUNK] for index in range(0, len(values), _IN_CHUNK)]


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class AssemblyCostItemInsert:
    node_level: int
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
class AssemblyCostIndirectInsert:
    code: str
    label: str
    amount: Decimal
    rate: Decimal | None
    base_amount: Decimal | None
    sort_no: int


@dataclass
class AssemblyCostUpsertPayload:
    year: int
    month: int
    location: str
    vehicle_model: str
    bom_version: str
    source_node_id: int
    level: int
    is_tree_root: bool
    parent_node_id: int | None
    root_part_number: str | None
    root_part_name: str | None
    procurement_object_id: int | None
    object_kind: str | None
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
    should_cost: Decimal
    vendor_quote: Decimal | None
    gap_amount: Decimal | None
    vendor_name: str | None
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
    items: list[AssemblyCostItemInsert]
    indirects: list[AssemblyCostIndirectInsert]


class AssemblyCostFilterSummary(TypedDict):
    """列表 HUD 汇总（全量筛选，非本页）。`total_amount_sum` 是月总账，看板不展示。"""

    total_count: int
    ok_count: int
    partial_count: int
    pending_count: int
    approved_count: int
    grand_total_sum: Decimal
    total_amount_sum: Decimal
    avg_grand_total: Decimal | None
    material_amount_sum: Decimal
    welding_amount_sum: Decimal


def empty_assembly_cost_summary() -> AssemblyCostFilterSummary:
    return {
        "total_count": 0,
        "ok_count": 0,
        "partial_count": 0,
        "pending_count": 0,
        "approved_count": 0,
        "grand_total_sum": Decimal("0"),
        "total_amount_sum": Decimal("0"),
        "avg_grand_total": None,
        "material_amount_sum": Decimal("0"),
        "welding_amount_sum": Decimal("0"),
    }


class AssemblyCostListFilters(TypedDict):
    year: int | None
    month: int | None
    location: str | None
    vehicle_model: str | None
    bom_version: str | None
    part_number: str | None
    audit_status: str | None
    calc_status: str | None
    view: str
    level: int | None
    object_kind: str | None
    summary: AssemblyCostFilterSummary


_MAIN_FIELDS = (
    "source_node_id",
    "level",
    "is_tree_root",
    "parent_node_id",
    "root_part_number",
    "root_part_name",
    "procurement_object_id",
    "object_kind",
    "part_number",
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
    "should_cost",
    "vendor_quote",
    "gap_amount",
    "vendor_name",
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


class AssemblyCostRepository:
    """成品月核价结果数据访问。"""

    def get_by_id(self, db: Session, cost_id: int) -> AssemblyCost | None:
        return (
            db.query(AssemblyCost)
            .options(
                joinedload(AssemblyCost.items),
                joinedload(AssemblyCost.indirects),
            )
            .filter(AssemblyCost.id == cost_id)
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
        source_node_id: int,
    ) -> AssemblyCost | None:
        return (
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.year == year,
                AssemblyCost.month == month,
                AssemblyCost.location == location,
                AssemblyCost.vehicle_model == vehicle_model,
                AssemblyCost.bom_version == bom_version,
                AssemblyCost.source_node_id == source_node_id,
            )
            .first()
        )

    def upsert_with_children(
        self, db: Session, payload: AssemblyCostUpsertPayload
    ) -> tuple[AssemblyCost, bool]:
        """写入主表并替换明细；返回 (row, created)。已审核行由 Service 跳过。"""
        existing = self.get_by_business_key(
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

    def _apply_filters(
        self,
        q: Query[_T],
        *,
        year: int | None,
        month: int | None,
        location: str | None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
        bom_version: str | None,
        part_number: str | None,
        audit_status: str | None,
        calc_status: str | None,
        view: str = "finance",
        level: int | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
    ) -> Query[_T]:
        if year is not None:
            q = q.filter(AssemblyCost.year == year)
        if month is not None:
            q = q.filter(AssemblyCost.month == month)
        if locations is not None:
            q = q.filter(AssemblyCost.location.in_(locations))
        elif location:
            q = q.filter(AssemblyCost.location == location)
        if vehicle_model:
            q = q.filter(AssemblyCost.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(AssemblyCost.bom_version == bom_version)
        if part_number:
            q = q.filter(AssemblyCost.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(AssemblyCost.audit_status == audit_status)
        if calc_status:
            q = q.filter(AssemblyCost.calc_status == calc_status)
        if level is not None:
            q = q.filter(AssemblyCost.level == level)
        if object_kind:
            q = q.filter(AssemblyCost.object_kind == object_kind)
        if view == "finance":
            q = q.filter(AssemblyCost.is_tree_root.is_(True))
        elif view == "procurement":
            q = q.filter(AssemblyCost.procurement_object_id.isnot(None))
        if confirm_status:
            from app.models.bom.procurement_object import BomProcurementObject

            q = q.join(
                BomProcurementObject,
                BomProcurementObject.id == AssemblyCost.procurement_object_id,
            ).filter(BomProcurementObject.confirm_status == confirm_status)
        return q

    @staticmethod
    def _order_like_bom_import(q: Query[_T]) -> Query[_T]:
        """与材料清单导入顺序一致：Excel 行序（BomNode.sort_no），不是零件号。"""
        return q.outerjoin(BomNode, BomNode.id == AssemblyCost.source_node_id).order_by(
            AssemblyCost.year.desc(),
            AssemblyCost.month.desc(),
            AssemblyCost.location.asc(),
            AssemblyCost.vehicle_model.asc(),
            AssemblyCost.bom_version.asc(),
            func.coalesce(BomNode.sort_no, BomNode.excel_row, 0).asc(),
            AssemblyCost.id.asc(),
        )

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        view: str = "finance",
        level: int | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AssemblyCost], int, AssemblyCostListFilters]:
        q = db.query(AssemblyCost)
        q = self._apply_filters(
            q,
            year=year,
            month=month,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            view=view,
            level=level,
            object_kind=object_kind,
            confirm_status=confirm_status,
        )
        total = q.count()
        rows = (
            self._order_like_bom_import(
                q.options(
                    noload(AssemblyCost.items),
                    noload(AssemblyCost.indirects),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        agg = self._apply_filters(
            db.query(
                func.count(AssemblyCost.id).label("total_count"),
                func.coalesce(
                    func.sum(case((AssemblyCost.calc_status == "ok", 1), else_=0)),
                    0,
                ).label("ok_count"),
                func.coalesce(
                    func.sum(case((AssemblyCost.calc_status == "partial", 1), else_=0)),
                    0,
                ).label("partial_count"),
                func.coalesce(
                    func.sum(case((AssemblyCost.audit_status == AUDIT_PENDING, 1), else_=0)),
                    0,
                ).label("pending_count"),
                func.coalesce(
                    func.sum(case((AssemblyCost.audit_status == AUDIT_APPROVED, 1), else_=0)),
                    0,
                ).label("approved_count"),
                func.coalesce(func.sum(AssemblyCost.grand_total), 0).label("grand_total_sum"),
                func.coalesce(func.sum(AssemblyCost.total_amount), 0).label("total_amount_sum"),
                func.avg(AssemblyCost.grand_total).label("avg_grand_total"),
                func.coalesce(func.sum(AssemblyCost.material_amount), 0).label(
                    "material_amount_sum"
                ),
                func.coalesce(func.sum(AssemblyCost.welding_amount), 0).label("welding_amount_sum"),
            ),
            year=year,
            month=month,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            view=view,
            level=level,
            object_kind=object_kind,
            confirm_status=confirm_status,
        ).one()
        avg_value = agg.avg_grand_total
        summary: AssemblyCostFilterSummary = {
            "total_count": int(agg.total_count or 0),
            "ok_count": int(agg.ok_count or 0),
            "partial_count": int(agg.partial_count or 0),
            "pending_count": int(agg.pending_count or 0),
            "approved_count": int(agg.approved_count or 0),
            "grand_total_sum": Decimal(str(agg.grand_total_sum or 0)),
            "total_amount_sum": Decimal(str(agg.total_amount_sum or 0)),
            "avg_grand_total": Decimal(str(avg_value)) if avg_value is not None else None,
            "material_amount_sum": Decimal(str(agg.material_amount_sum or 0)),
            "welding_amount_sum": Decimal(str(agg.welding_amount_sum or 0)),
        }
        filters: AssemblyCostListFilters = {
            "year": year,
            "month": month,
            "location": location,
            "vehicle_model": vehicle_model,
            "bom_version": bom_version,
            "part_number": part_number,
            "audit_status": audit_status,
            "calc_status": calc_status,
            "view": view,
            "level": level,
            "object_kind": object_kind,
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
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        view: str = "finance",
        level: int | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
    ) -> list[AssemblyCost]:
        """按筛选导出：主表 + items + indirects。"""
        q = db.query(AssemblyCost)
        q = self._apply_filters(
            q,
            year=year,
            month=month,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            view=view,
            level=level,
            object_kind=object_kind,
            confirm_status=confirm_status,
        )
        ordered_ids = [
            int(row[0])
            for row in self._order_like_bom_import(q.with_entities(AssemblyCost.id)).all()
        ]
        if not ordered_ids:
            return []
        loaded = (
            db.query(AssemblyCost)
            .options(
                joinedload(AssemblyCost.items),
                joinedload(AssemblyCost.indirects),
            )
            .filter(AssemblyCost.id.in_(ordered_ids))
            .all()
        )
        by_id = {int(record.id): record for record in loaded}
        return [by_id[cost_id] for cost_id in ordered_ids if cost_id in by_id]

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
        view: str = "finance",
    ) -> list[int]:
        q = db.query(AssemblyCost.id).filter(
            AssemblyCost.year == year,
            AssemblyCost.month == month,
            AssemblyCost.location == location,
            AssemblyCost.vehicle_model == vehicle_model,
            AssemblyCost.bom_version == bom_version,
        )
        if view == "finance":
            q = q.filter(AssemblyCost.is_tree_root.is_(True))
        elif view == "procurement":
            q = q.filter(AssemblyCost.procurement_object_id.isnot(None))
        if only_pending:
            q = q.filter(AssemblyCost.audit_status == AUDIT_PENDING)
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
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.year == year,
                AssemblyCost.month == month,
                AssemblyCost.location == location,
                AssemblyCost.vehicle_model == vehicle_model,
                AssemblyCost.bom_version == bom_version,
                AssemblyCost.audit_status == AUDIT_APPROVED,
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

    def count_approved_by_ids(self, db: Session, ids: list[int]) -> int:
        if not ids:
            return 0
        return (
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.id.in_(ids),
                AssemblyCost.audit_status == AUDIT_APPROVED,
            )
            .count()
        )

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

    def list_by_scope_source_nodes(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        source_node_ids: list[int],
    ) -> list[AssemblyCost]:
        if not source_node_ids:
            return []
        rows: list[AssemblyCost] = []
        for chunk in _chunks(source_node_ids):
            rows.extend(
                db.query(AssemblyCost)
                .options(noload(AssemblyCost.items), noload(AssemblyCost.indirects))
                .filter(
                    AssemblyCost.year == year,
                    AssemblyCost.month == month,
                    AssemblyCost.location == location,
                    AssemblyCost.vehicle_model == vehicle_model,
                    AssemblyCost.bom_version == bom_version,
                    AssemblyCost.source_node_id.in_(chunk),
                )
                .all()
            )
        return rows

    def list_by_part_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        part_number: str,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
    ) -> list[AssemblyCost]:
        query = (
            db.query(AssemblyCost)
            .options(noload(AssemblyCost.items), noload(AssemblyCost.indirects))
            .filter(
                AssemblyCost.year == year,
                AssemblyCost.month == month,
                AssemblyCost.part_number == part_number,
            )
        )
        if location:
            query = query.filter(AssemblyCost.location == location)
        if vehicle_model:
            query = query.filter(AssemblyCost.vehicle_model == vehicle_model)
        if bom_version:
            query = query.filter(AssemblyCost.bom_version == bom_version)
        return query.order_by(AssemblyCost.id.asc()).all()

    def list_should_costs_for_nodes(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        months: list[tuple[int, int]],
        source_node_ids: list[int],
        amount_field: SettlementAmountField = "total_amount",
    ) -> list[tuple[int, int, int, Decimal]]:
        """窗口内节点结算价。采购对象抄总成本，总成抄总费用。"""
        if not months or not source_node_ids:
            return []
        amount_column = _SETTLEMENT_AMOUNT_COLUMNS[amount_field]
        month_clause = or_(
            *[
                and_(AssemblyCost.year == year, AssemblyCost.month == month)
                for year, month in months
            ]
        )
        rows: list[tuple[int, int, int, Decimal]] = []
        for chunk in _chunks(source_node_ids):
            found = (
                db.query(
                    AssemblyCost.year,
                    AssemblyCost.month,
                    AssemblyCost.source_node_id,
                    amount_column,
                )
                .filter(
                    AssemblyCost.location == location,
                    AssemblyCost.vehicle_model == vehicle_model,
                    AssemblyCost.bom_version == bom_version,
                    month_clause,
                    AssemblyCost.source_node_id.in_(chunk),
                )
                .all()
            )
            rows.extend(
                (int(year), int(month), int(node_id), _decimal(amount))
                for year, month, node_id, amount in found
            )
        return rows

    def list_distinct_years(self, db: Session) -> list[int]:
        rows = db.query(AssemblyCost.year).distinct().order_by(AssemblyCost.year.desc()).all()
        return [int(r[0]) for r in rows]

    def get_latest_scope_year_month(self, db: Session) -> tuple[str, str, str, int, int] | None:
        """全库最近一次核价月及其基地/项目/版本。"""
        row = (
            db.query(
                AssemblyCost.location,
                AssemblyCost.vehicle_model,
                AssemblyCost.bom_version,
                AssemblyCost.year,
                AssemblyCost.month,
            )
            .order_by(
                AssemblyCost.year.desc(),
                AssemblyCost.month.desc(),
                AssemblyCost.id.desc(),
            )
            .first()
        )
        if row is None:
            return None
        return str(row[0]), str(row[1]), str(row[2]), int(row[3]), int(row[4])
