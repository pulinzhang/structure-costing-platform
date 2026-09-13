"""按月聚合树根核价卡。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.costing.assembly_cost import AssemblyCost
from app.repositories.llm._query_guard import run_guarded_query
from app.repositories.llm.cost_analysis.missing import is_missing_price
from app.repositories.llm.cost_analysis.rows import L0MonthlyTotalRow
from app.repositories.llm.cost_analysis.scope import apply_assembly_cost_scope
from app.services.llm._money import ym_int


class L0MonthlyTotalsRepository:
    def query_monthly_totals(
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
        locations: list[str] | None = None,
        trace_id: str | None = None,
    ) -> list[L0MonthlyTotalRow]:
        """按月从 L0 明细表实时聚合。"""
        return run_guarded_query(
            sql_summary="costing_assembly_costs.query_monthly_totals",
            trace_id=trace_id,
            query_fn=lambda: self._query_monthly_totals_impl(
                db,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                start_year=start_year,
                start_month=start_month,
                end_year=end_year,
                end_month=end_month,
                locations=locations,
            ),
        )

    def count_filtered_missing_price(
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
        trace_id: str | None = None,
    ) -> int:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = AssemblyCost.year * 100 + AssemblyCost.month

        def _count() -> int:
            q = db.query(func.count(AssemblyCost.id)).filter(
                ym_expr >= start,
                ym_expr <= end,
                AssemblyCost.is_tree_root.is_(True),
                is_missing_price(),
            )
            q = apply_assembly_cost_scope(
                q,
                db,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
            )
            return int(q.scalar() or 0)

        return run_guarded_query(
            sql_summary="costing_assembly_costs.count_missing_price",
            trace_id=trace_id,
            query_fn=_count,
        )

    def _query_monthly_totals_impl(
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
        locations: list[str] | None,
    ) -> list[L0MonthlyTotalRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = AssemblyCost.year * 100 + AssemblyCost.month
        missing = is_missing_price()

        priced = case(
            (missing, 0),
            else_=AssemblyCost.grand_total,
        )
        ok_count = func.sum(case((AssemblyCost.calc_status == "ok", 1), else_=0))
        partial_count = func.sum(case((AssemblyCost.calc_status != "ok", 1), else_=0))
        missing_price_count = func.sum(case((missing, 1), else_=0))

        q = db.query(
            AssemblyCost.year,
            AssemblyCost.month,
            AssemblyCost.location,
            func.count(AssemblyCost.id),
            ok_count,
            partial_count,
            func.coalesce(func.sum(priced), 0),
            func.coalesce(
                func.sum(case((missing, 0), else_=AssemblyCost.total_amount)),
                0,
            ),
            func.coalesce(
                func.sum(case((missing, 0), else_=AssemblyCost.indirect_amount)),
                0,
            ),
            func.coalesce(
                func.sum(case((missing, 0), else_=AssemblyCost.stamping_amount)),
                0,
            ),
            func.coalesce(
                func.sum(case((missing, 0), else_=AssemblyCost.purchased_amount)),
                0,
            ),
            func.coalesce(
                func.sum(case((missing, 0), else_=AssemblyCost.bundle_amount)),
                0,
            ),
            func.coalesce(
                func.sum(case((missing, 0), else_=AssemblyCost.welding_amount)),
                0,
            ),
            func.coalesce(
                func.sum(case((missing, 0), else_=AssemblyCost.welding_other_fee)),
                0,
            ),
            missing_price_count,
        ).filter(
            ym_expr >= start,
            ym_expr <= end,
            AssemblyCost.is_tree_root.is_(True),
        )
        q = apply_assembly_cost_scope(
            q,
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            locations=locations,
        )
        q = q.group_by(
            AssemblyCost.year,
            AssemblyCost.month,
            AssemblyCost.location,
        ).order_by(
            AssemblyCost.location.asc(),
            AssemblyCost.year.asc(),
            AssemblyCost.month.asc(),
        )

        rows: list[L0MonthlyTotalRow] = []
        for item in q.all():
            rows.append(
                L0MonthlyTotalRow(
                    year=int(item[0]),
                    month=int(item[1]),
                    location=str(item[2]),
                    l0_count=int(item[3] or 0),
                    ok_count=int(item[4] or 0),
                    partial_count=int(item[5] or 0),
                    grand_total_sum=Decimal(str(item[6] or 0)),
                    total_amount_sum=Decimal(str(item[7] or 0)),
                    indirect_amount_sum=Decimal(str(item[8] or 0)),
                    stamping_amount_sum=Decimal(str(item[9] or 0)),
                    purchased_amount_sum=Decimal(str(item[10] or 0)),
                    bundle_amount_sum=Decimal(str(item[11] or 0)),
                    welding_amount_sum=Decimal(str(item[12] or 0)),
                    welding_other_amount_sum=Decimal(str(item[13] or 0)),
                    missing_price_count=int(item[14] or 0),
                )
            )
        return rows
