"""L0 成品核价结果 — 只读查询 / SQL 查询聚合。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.common.part_number import escape_like_fragment
from app.models.costing.l0_assembly_cost import L0AssemblyCost
from app.models.llm.monthly_cost_summary import LlmMonthlyCostSummary
from app.repositories.llm._query_guard import run_guarded_query
from app.services.llm._money import ym_int


@dataclass(frozen=True, slots=True)
class L0MonthlyTotalRow:
    year: int
    month: int
    location: str
    l0_count: int
    ok_count: int
    partial_count: int
    grand_total_sum: Decimal
    total_amount_sum: Decimal
    indirect_amount_sum: Decimal
    stamping_amount_sum: Decimal
    purchased_amount_sum: Decimal
    bundle_amount_sum: Decimal
    welding_amount_sum: Decimal
    welding_other_amount_sum: Decimal
    missing_price_count: int = 0


@dataclass(frozen=True, slots=True)
class L0PartPeriodRow:
    year: int
    month: int
    part_number: str
    part_name: str | None
    grand_total: Decimal
    total_amount: Decimal
    calc_status: str
    missing_leaf_count: int
    calc_message: str | None
    stamping_amount: Decimal
    purchased_amount: Decimal
    bundle_amount: Decimal
    welding_amount: Decimal
    welding_other_fee: Decimal
    indirect_amount: Decimal
    bom_version: str


def _is_missing_price() -> ColumnElement[bool]:
    return or_(
        L0AssemblyCost.grand_total.is_(None),
        L0AssemblyCost.grand_total <= 0,
    )


class L0CostAnalysisRepository:
    """禁止业务分析逻辑（MoM/贡献度等）；仅 WHERE / GROUP BY / SUM。"""

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
        summary_rows = run_guarded_query(
            sql_summary="llm_monthly_cost_summary.query_monthly_totals",
            trace_id=trace_id,
            query_fn=lambda: self._query_monthly_from_summary(
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
        if summary_rows:
            return summary_rows

        detail_rows = run_guarded_query(
            sql_summary="costing_l0_assembly_costs.query_monthly_totals",
            trace_id=trace_id,
            query_fn=lambda: self._query_monthly_from_detail(
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
        if detail_rows:
            self._refresh_monthly_summary(db, detail_rows)
        return detail_rows

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
        trace_id: str | None = None,
    ) -> list[L0PartPeriodRow]:
        return run_guarded_query(
            sql_summary="costing_l0_assembly_costs.query_part_rows",
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
        ym_expr = L0AssemblyCost.year * 100 + L0AssemblyCost.month

        def _count() -> int:
            q = db.query(func.count(L0AssemblyCost.id)).filter(
                ym_expr >= start,
                ym_expr <= end,
                _is_missing_price(),
            )
            if location:
                q = q.filter(L0AssemblyCost.location == location)
            if vehicle_model:
                q = q.filter(L0AssemblyCost.vehicle_model == vehicle_model)
            if bom_version:
                q = q.filter(L0AssemblyCost.bom_version == bom_version)
            return int(q.scalar() or 0)

        return run_guarded_query(
            sql_summary="costing_l0_assembly_costs.count_missing_price",
            trace_id=trace_id,
            query_fn=_count,
        )

    def _query_monthly_from_summary(
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
        ym_expr = LlmMonthlyCostSummary.year * 100 + LlmMonthlyCostSummary.month

        q = db.query(LlmMonthlyCostSummary).filter(ym_expr >= start, ym_expr <= end)
        if locations:
            q = q.filter(LlmMonthlyCostSummary.location.in_(locations))
        elif location:
            q = q.filter(LlmMonthlyCostSummary.location == location)
        if vehicle_model:
            q = q.filter(LlmMonthlyCostSummary.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(LlmMonthlyCostSummary.bom_version == bom_version)

        rows = q.order_by(
            LlmMonthlyCostSummary.location.asc(),
            LlmMonthlyCostSummary.year.asc(),
            LlmMonthlyCostSummary.month.asc(),
        ).all()
        if not rows:
            return []

        return [
            L0MonthlyTotalRow(
                year=int(row.year),
                month=int(row.month),
                location=str(row.location),
                l0_count=int(row.l0_count or 0),
                ok_count=int(row.ok_count or 0),
                partial_count=int(row.partial_count or 0),
                grand_total_sum=Decimal(str(row.grand_total_sum or 0)),
                total_amount_sum=Decimal(str(row.total_amount_sum or 0)),
                indirect_amount_sum=Decimal(str(row.indirect_amount_sum or 0)),
                stamping_amount_sum=Decimal(str(row.stamping_amount_sum or 0)),
                purchased_amount_sum=Decimal(str(row.purchased_amount_sum or 0)),
                bundle_amount_sum=Decimal(str(row.bundle_amount_sum or 0)),
                welding_amount_sum=Decimal(str(row.welding_amount_sum or 0)),
                welding_other_amount_sum=Decimal(str(row.welding_other_amount_sum or 0)),
                missing_price_count=int(row.missing_price_count or 0),
            )
            for row in rows
        ]

    def _query_monthly_from_detail(
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
        ym_expr = L0AssemblyCost.year * 100 + L0AssemblyCost.month

        priced = case(
            (_is_missing_price(), 0),
            else_=L0AssemblyCost.grand_total,
        )
        ok_count = func.sum(
            case((L0AssemblyCost.calc_status == "ok", 1), else_=0)
        )
        partial_count = func.sum(
            case((L0AssemblyCost.calc_status != "ok", 1), else_=0)
        )
        missing_price_count = func.sum(
            case((_is_missing_price(), 1), else_=0)
        )

        q = db.query(
            L0AssemblyCost.year,
            L0AssemblyCost.month,
            L0AssemblyCost.location,
            func.count(L0AssemblyCost.id),
            ok_count,
            partial_count,
            func.coalesce(func.sum(priced), 0),
            func.coalesce(
                func.sum(
                    case((_is_missing_price(), 0), else_=L0AssemblyCost.total_amount)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((_is_missing_price(), 0), else_=L0AssemblyCost.indirect_amount)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((_is_missing_price(), 0), else_=L0AssemblyCost.stamping_amount)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (_is_missing_price(), 0),
                        else_=L0AssemblyCost.purchased_amount,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((_is_missing_price(), 0), else_=L0AssemblyCost.bundle_amount)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((_is_missing_price(), 0), else_=L0AssemblyCost.welding_amount)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (_is_missing_price(), 0),
                        else_=L0AssemblyCost.welding_other_fee,
                    )
                ),
                0,
            ),
            missing_price_count,
        ).filter(ym_expr >= start, ym_expr <= end)

        if locations:
            q = q.filter(L0AssemblyCost.location.in_(locations))
        elif location:
            q = q.filter(L0AssemblyCost.location == location)
        if vehicle_model:
            q = q.filter(L0AssemblyCost.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(L0AssemblyCost.bom_version == bom_version)

        q = q.group_by(
            L0AssemblyCost.year,
            L0AssemblyCost.month,
            L0AssemblyCost.location,
        ).order_by(
            L0AssemblyCost.location.asc(),
            L0AssemblyCost.year.asc(),
            L0AssemblyCost.month.asc(),
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
    ) -> list[L0PartPeriodRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = L0AssemblyCost.year * 100 + L0AssemblyCost.month

        q = db.query(L0AssemblyCost).filter(ym_expr >= start, ym_expr <= end)
        if location:
            q = q.filter(L0AssemblyCost.location == location)
        if vehicle_model:
            q = q.filter(L0AssemblyCost.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(L0AssemblyCost.bom_version == bom_version)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(L0AssemblyCost.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            L0AssemblyCost.year.asc(),
            L0AssemblyCost.month.asc(),
            L0AssemblyCost.grand_total.desc(),
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
            )
            for row in q.all()
        ]

    def _refresh_monthly_summary(
        self,
        db: Session,
        rows: list[L0MonthlyTotalRow],
    ) -> None:
        """明细降级查询后回写预聚合表（懒刷新）。"""
        if not rows:
            return
        for row in rows:
            existing = (
                db.query(LlmMonthlyCostSummary)
                .filter(
                    LlmMonthlyCostSummary.year == row.year,
                    LlmMonthlyCostSummary.month == row.month,
                    LlmMonthlyCostSummary.location == row.location,
                )
                .first()
            )
            if existing is not None:
                continue
            db.add(
                LlmMonthlyCostSummary(
                    year=row.year,
                    month=row.month,
                    location=row.location,
                    vehicle_model="*",
                    bom_version="*",
                    l0_count=row.l0_count,
                    ok_count=row.ok_count,
                    partial_count=row.partial_count,
                    missing_price_count=row.missing_price_count,
                    grand_total_sum=row.grand_total_sum,
                    total_amount_sum=row.total_amount_sum,
                    indirect_amount_sum=row.indirect_amount_sum,
                    stamping_amount_sum=row.stamping_amount_sum,
                    purchased_amount_sum=row.purchased_amount_sum,
                    bundle_amount_sum=row.bundle_amount_sum,
                    welding_amount_sum=row.welding_amount_sum,
                    welding_other_amount_sum=row.welding_other_amount_sum,
                    created_by="system",
                    updated_by="system",
                )
            )
        db.flush()
