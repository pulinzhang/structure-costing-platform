"""最新核价卡范围与卡上材料行。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.repositories.llm._query_guard import run_guarded_query
from app.repositories.llm.cost_analysis.rows import AssemblyCardItemRow, LatestAssemblyCardScope
from app.repositories.llm.cost_analysis.scope import apply_assembly_cost_scope
from app.repositories.llm.location_in import location_in_clause


class L0CardRepository:
    def query_latest_card_scope(
        self,
        db: Session,
        *,
        part_number: str | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        trace_id: str | None = None,
    ) -> LatestAssemblyCardScope | None:
        """核价表内最新年月的一张卡：同年月优先树根总成。"""
        return run_guarded_query(
            sql_summary="costing_assembly_costs.query_latest_card_scope",
            trace_id=trace_id,
            query_fn=lambda: self._query_latest_card_scope_impl(
                db,
                part_number=part_number,
                location=location,
                vehicle_model=vehicle_model,
            ),
        )

    def query_card_item_rows(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        part_number: str,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        limit: int = 200,
        trace_id: str | None = None,
    ) -> list[AssemblyCardItemRow]:
        return run_guarded_query(
            sql_summary="costing_assembly_cost_items.query_card_item_rows",
            trace_id=trace_id,
            query_fn=lambda: self._query_card_item_rows_impl(
                db,
                year=year,
                month=month,
                part_number=part_number,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                limit=limit,
            ),
        )

    def _query_latest_card_scope_impl(
        self,
        db: Session,
        *,
        part_number: str | None,
        location: str | None,
        vehicle_model: str | None,
    ) -> LatestAssemblyCardScope | None:
        q = db.query(AssemblyCost)
        loc_filter = location_in_clause(db, AssemblyCost.location, location)
        if loc_filter is not None:
            q = q.filter(loc_filter)
        if vehicle_model:
            q = q.filter(AssemblyCost.vehicle_model == vehicle_model)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(AssemblyCost.part_number.like(pattern, escape="\\"))
        row = q.order_by(
            AssemblyCost.year.desc(),
            AssemblyCost.month.desc(),
            AssemblyCost.is_tree_root.desc(),
            AssemblyCost.id.desc(),
        ).first()
        if row is None and part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            item_q = (
                db.query(AssemblyCost)
                .join(
                    AssemblyCostItem,
                    AssemblyCostItem.assembly_cost_id == AssemblyCost.id,
                )
                .filter(AssemblyCostItem.part_number.like(pattern, escape="\\"))
            )
            loc_filter = location_in_clause(db, AssemblyCost.location, location)
            if loc_filter is not None:
                item_q = item_q.filter(loc_filter)
            if vehicle_model:
                item_q = item_q.filter(AssemblyCost.vehicle_model == vehicle_model)
            row = item_q.order_by(
                AssemblyCost.year.desc(),
                AssemblyCost.month.desc(),
                AssemblyCost.is_tree_root.desc(),
                AssemblyCost.id.desc(),
            ).first()
        if row is None:
            return None
        return LatestAssemblyCardScope(
            year=int(row.year),
            month=int(row.month),
            location=str(row.location) if row.location else None,
            vehicle_model=str(row.vehicle_model) if row.vehicle_model else None,
            bom_version=str(row.bom_version) if row.bom_version else None,
            part_number=str(row.part_number),
            is_tree_root=bool(row.is_tree_root),
            object_kind=str(row.object_kind) if row.object_kind else None,
            root_part_number=str(row.root_part_number) if row.root_part_number else None,
        )

    def _query_card_item_rows_impl(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        part_number: str,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        limit: int,
    ) -> list[AssemblyCardItemRow]:
        pattern = f"%{escape_like_fragment(part_number)}%"
        q = (
            db.query(AssemblyCostItem)
            .join(AssemblyCost, AssemblyCostItem.assembly_cost_id == AssemblyCost.id)
            .filter(
                AssemblyCost.year == year,
                AssemblyCost.month == month,
                AssemblyCost.part_number.like(pattern, escape="\\"),
            )
        )
        q = apply_assembly_cost_scope(
            q,
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        q = q.order_by(AssemblyCostItem.sort_no.asc(), AssemblyCostItem.id.asc()).limit(limit)
        rows: list[AssemblyCardItemRow] = []
        for item in q.all():
            rows.append(
                AssemblyCardItemRow(
                    child_part_number=str(item.part_number),
                    child_part_name=item.part_name,
                    cost_source=str(item.cost_source or ""),
                    unit_price=Decimal(str(item.unit_price or 0)),
                    effective_qty=Decimal(str(item.effective_qty or 0)),
                    line_amount=Decimal(str(item.line_amount or 0)),
                    supply_type=item.supply_type,
                    node_level=int(item.node_level or 0),
                )
            )
        return rows
