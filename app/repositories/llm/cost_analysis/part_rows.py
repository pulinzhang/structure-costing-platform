"""核价卡零件期间行。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment
from app.models.costing.assembly_cost import AssemblyCost
from app.repositories.llm._query_guard import run_guarded_query
from app.repositories.llm.cost_analysis.rows import L0PartPeriodRow
from app.repositories.llm.cost_analysis.scope import apply_assembly_cost_scope
from app.services.llm._money import ym_int


class L0PartRowRepository:
    def query_part_rows(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        part_number: str | None = None,
        limit: int = 5000,
        tree_root_only: bool = True,
        trace_id: str | None = None,
    ) -> list[L0PartPeriodRow]:
        return run_guarded_query(
            sql_summary="costing_assembly_costs.query_part_rows",
            trace_id=trace_id,
            query_fn=lambda: self._query_part_rows_impl(
                db,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                start_year=start_year,
                start_month=start_month,
                end_year=end_year,
                end_month=end_month,
                part_number=part_number,
                limit=limit,
                tree_root_only=tree_root_only,
            ),
        )

    def _query_part_rows_impl(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        part_number: str | None,
        limit: int,
        tree_root_only: bool,
    ) -> list[L0PartPeriodRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = AssemblyCost.year * 100 + AssemblyCost.month

        q = db.query(AssemblyCost).filter(
            ym_expr >= start,
            ym_expr <= end,
        )
        if tree_root_only:
            q = q.filter(AssemblyCost.is_tree_root.is_(True))
        q = apply_assembly_cost_scope(
            q,
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(AssemblyCost.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            AssemblyCost.year.asc(),
            AssemblyCost.month.asc(),
            AssemblyCost.grand_total.desc(),
        ).limit(limit)

        return [
            L0PartPeriodRow(
                year=int(row.year),
                month=int(row.month),
                part_number=str(row.part_number),
                part_name=row.part_name,
                grand_total=Decimal(str(row.grand_total or 0)),
                total_amount=Decimal(str(row.total_amount or 0)),
                calc_status=str(row.calc_status or "ok"),
                missing_leaf_count=int(row.missing_leaf_count or 0),
                calc_message=row.calc_message,
                stamping_amount=Decimal(str(row.stamping_amount or 0)),
                purchased_amount=Decimal(str(row.purchased_amount or 0)),
                bundle_amount=Decimal(str(row.bundle_amount or 0)),
                welding_amount=Decimal(str(row.welding_amount or 0)),
                welding_other_fee=Decimal(str(row.welding_other_fee or 0)),
                indirect_amount=Decimal(str(row.indirect_amount or 0)),
                bom_version=str(row.bom_version),
                should_cost=Decimal(str(row.should_cost or row.total_amount or 0)),
                level=int(row.level or 0),
                is_tree_root=bool(row.is_tree_root),
                object_kind=str(row.object_kind) if row.object_kind else None,
                location=str(row.location) if row.location else None,
                vehicle_model=str(row.vehicle_model) if row.vehicle_model else None,
                root_part_number=str(row.root_part_number) if row.root_part_number else None,
            )
            for row in q.all()
        ]
