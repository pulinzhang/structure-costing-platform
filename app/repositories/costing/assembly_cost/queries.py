"""成品月核价查询：列表、导出、范围、结算价窗口。

写入在 writes.py。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TypeVar

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Query, Session, joinedload, noload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.common.bom.node_order import MISSING_SEQ_NO
from app.models.bom.node import BomNode
from app.models.costing.assembly_cost import AssemblyCost
from app.repositories.costing.assembly_cost.payloads import (
    _SETTLEMENT_AMOUNT_COLUMNS,
    AssemblyCostFilterSummary,
    AssemblyCostListFilters,
    SettlementAmountField,
    _chunks,
    _decimal,
)

_T = TypeVar("_T")


class AssemblyCostQueries:
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
        """列表/导出序：年 → 月 → 基地 → 项目 → L0 seq_no。

        财务树根的 source_node_id 即 L0；采购视图在同键后再按 level / excel_row 收束。
        """
        return q.outerjoin(BomNode, BomNode.id == AssemblyCost.source_node_id).order_by(
            AssemblyCost.year.desc(),
            AssemblyCost.month.desc(),
            AssemblyCost.location.asc(),
            AssemblyCost.vehicle_model.asc(),
            func.coalesce(BomNode.seq_no, MISSING_SEQ_NO).asc(),
            BomNode.level.asc(),
            case((BomNode.level == 0, BomNode.part_number), else_="").asc(),
            func.coalesce(BomNode.excel_row, BomNode.sort_no, 0).asc(),
            BomNode.part_number.asc(),
            func.coalesce(BomNode.sort_no, 0).asc(),
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
        bom_version: str | None = None,
        only_pending: bool = False,
        view: str = "finance",
    ) -> list[int]:
        q = db.query(AssemblyCost.id).filter(
            AssemblyCost.year == year,
            AssemblyCost.month == month,
            AssemblyCost.location == location,
            AssemblyCost.vehicle_model == vehicle_model,
        )
        if bom_version:
            q = q.filter(AssemblyCost.bom_version == bom_version)
        if view == "finance":
            q = q.filter(AssemblyCost.is_tree_root.is_(True))
        elif view == "procurement":
            q = q.filter(AssemblyCost.procurement_object_id.isnot(None))
        if only_pending:
            q = q.filter(AssemblyCost.audit_status == AUDIT_PENDING)
        return [row[0] for row in q.all()]

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
        months: list[tuple[int, int]],
        source_node_ids: list[int],
        amount_field: SettlementAmountField = "total_amount",
        bom_version: str | None = None,
    ) -> list[tuple[int, int, int, Decimal]]:
        """窗口内节点结算价。采购对象抄总成本，总成抄总费用。不按版本滤卡（除非浏览筛）。"""
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
            query = db.query(
                AssemblyCost.year,
                AssemblyCost.month,
                AssemblyCost.source_node_id,
                amount_column,
            ).filter(
                AssemblyCost.location == location,
                AssemblyCost.vehicle_model == vehicle_model,
                month_clause,
                AssemblyCost.source_node_id.in_(chunk),
            )
            if bom_version:
                query = query.filter(AssemblyCost.bom_version == bom_version)
            found = query.all()
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
        source_node_id: int,
    ) -> AssemblyCost | None:
        return (
            db.query(AssemblyCost)
            .filter(
                AssemblyCost.year == year,
                AssemblyCost.month == month,
                AssemblyCost.location == location,
                AssemblyCost.vehicle_model == vehicle_model,
                AssemblyCost.source_node_id == source_node_id,
            )
            .first()
        )
