"""联动价 / 加减价政策 / 基价 / 中标厚度 / 废料。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.llm.base_price_analysis_repository import BasePriceAnalysisRepository
from app.repositories.llm.policy_analysis_repository import PolicyAnalysisRepository
from app.repositories.llm.scrap_price_analysis_repository import ScrapPriceAnalysisRepository
from app.repositories.llm.steel_price_analysis_repository import SteelPriceAnalysisRepository
from app.schemas.llm.analysis_payload import (
    AnalysisResultLeafPayload,
)
from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm._money import money_str
from app.services.llm.analysis.shared.compose import compose_result
from app.services.llm.analysis.shared.cost_trend import build_steel_trend
from app.services.llm.analysis.shared.result import AnalysisRunResult
from app.services.llm.analysis.shared.summary import build_steel_summary
from app.services.llm.analysis.steel.base_price import (
    build_base_price_drivers,
    build_base_price_mom_anomalies,
    build_base_price_month_move_over,
    build_base_price_summary,
    build_base_price_trend,
)
from app.services.llm.analysis.steel.policy import (
    build_policy_drivers,
    build_policy_mom_anomalies,
    build_policy_summary,
    build_policy_trend,
)
from app.services.llm.analysis.steel.scrap import (
    build_scrap_price_drivers,
    build_scrap_price_summary,
)
from app.services.llm.analysis.steel.winning_thickness import (
    build_winning_thickness_drivers,
    build_winning_thickness_summary,
    load_winning_thickness_rows,
)
from app.services.llm.comparison_basis import resolve_comparability
from app.services.masterdata.steel_mill.service import SteelMillService
from app.services.yishiyiyi.winning_thickness.export.service import (
    WinningThicknessExportService,
)


class SteelAnalysis:
    def __init__(self) -> None:
        self._steel_repo = SteelPriceAnalysisRepository()
        self._policy_repo = PolicyAnalysisRepository()
        self._base_price_repo = BasePriceAnalysisRepository()
        self._winning_thickness_export = WinningThicknessExportService()
        self._scrap_price_repo = ScrapPriceAnalysisRepository()

    def run_steel_price_policy(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「加减价政策列表」#/steel-price-policy-download。"""
        tr = query.time_range
        policy_type = query.filter_get("policy_type")
        asked_mill = query.filter_get("steel_mill")
        mill_id: int | None = None
        if asked_mill:
            hit = SteelMillService().resolve(db, asked_mill)
            if hit is None:
                return AnalysisRunResult(
                    comparability=resolve_comparability(query.comparison_basis),
                    has_data=False,
                    data_message="当前范围无加减价政策数据",
                )
            mill_id = hit.id
        rows = self._policy_repo.query_ladder_rows(
            db,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            steel_mill_id=mill_id,
            category_name=query.filter_get("category_name"),
            policy_type=policy_type,
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"加减价阶梯行={len(rows)}" if rows else "当前范围无加减价政策数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_policy_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_policy_drivers(rows)
        if "trend" in query.analyses and rows:
            parts_result["trend"] = build_policy_trend(rows, basis=query.comparison_basis)
        if rows and query.time_range.month_span() > 1:
            parts_result["policy_anomalies"] = build_policy_mom_anomalies(rows)
        out.result = compose_result(parts_result, default_kind="summary")
        out.evidence["policy_ladder_rows"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "steel_mill": row.steel_mill,
                "category_name": row.category_name,
                "policy_type": row.policy_type,
                "grade_value": row.grade_value,
                "price_adjustment": row.price_adjustment,
                "thick_min": str(row.thick_min) if row.thick_min is not None else None,
                "thick_max": str(row.thick_max) if row.thick_max is not None else None,
            }
            for row in rows[:50]
        ]
        return out

    def run_steel_base_price(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「基准价格列表」#/base-price-download。"""
        over_text = query.filter_get("month_move_over")
        if over_text is not None:
            return self._run_base_price_month_move(db, query, Decimal(over_text))
        tr = query.time_range
        rows = self._base_price_repo.query_rows(
            db,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            location=query.location(),
            steel_mill=query.filter_get("steel_mill"),
            category_name=query.filter_get("category_name"),
            grade=query.filter_get("grade"),
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"基准价行={len(rows)}" if rows else "当前范围无基准价格数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_base_price_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_base_price_drivers(rows)
        if "trend" in query.analyses and rows:
            parts_result["trend"] = build_base_price_trend(rows, basis=query.comparison_basis)
        if rows and query.time_range.month_span() > 1:
            parts_result["base_price_anomalies"] = build_base_price_mom_anomalies(rows)
        out.result = compose_result(parts_result, default_kind="summary")
        out.evidence["base_price_rows"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "location": row.location,
                "steel_mill": row.steel_mill,
                "grade": row.grade,
                "spec": row.spec,
                "base_price": money_str(row.base_price),
            }
            for row in rows[:50]
        ]
        return out

    def _run_base_price_month_move(
        self,
        db: Session,
        query: AnalysisQuery,
        limit: Decimal,
    ) -> AnalysisRunResult:
        """问句里点了相差金额。只列单价加加工费的环比，不混入均价异常。"""
        tr = query.time_range
        if tr.start_month <= 1:
            start_year, start_month = tr.start_year - 1, 12
        else:
            start_year, start_month = tr.start_year, tr.start_month - 1
        rows = self._base_price_repo.query_rows(
            db,
            start_year=start_year,
            start_month=start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            location=query.location(),
            steel_mill=query.filter_get("steel_mill"),
            category_name=query.filter_get("category_name"),
            grade=query.filter_get("grade"),
            limit=50_000,
        )
        window_start = (tr.start_year, tr.start_month)
        in_window = [row for row in rows if (row.year, row.month) >= window_start]
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(in_window),
            data_message="" if in_window else "当前范围无基准价格数据",
        )
        if not in_window:
            return out
        payload = build_base_price_month_move_over(rows, limit=limit, window_start=window_start)
        out.data_message = str(payload.get("note") or "")
        out.result = payload
        return out

    def run_winning_thickness(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「中标钢厂厚度价格列表」#/winning-thickness-download。"""
        tr = query.time_range
        location = (query.location() or "").strip()
        if not location:
            return AnalysisRunResult(
                comparability=resolve_comparability(query.comparison_basis),
                has_data=False,
                data_message="中标厚度价须指定基地",
            )

        rows = load_winning_thickness_rows(
            self._winning_thickness_export,
            db,
            year=tr.end_year,
            month=tr.end_month,
            location=location,
            steel_mill=query.filter_get("steel_mill"),
            category_name=query.filter_get("category_name"),
            grade=query.filter_get("grade"),
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"中标厚度价行={len(rows)}" if rows else "当前范围无中标厚度价数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_winning_thickness_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_winning_thickness_drivers(rows)
        out.result = compose_result(parts_result, default_kind="summary")
        out.evidence["winning_thickness_rows"] = [
            {
                "steel_mill": row.steel_mill,
                "category_name": row.category_name,
                "grade": row.grade,
                "thickness_range": row.thickness_range,
                "final_price": money_str(row.final_price),
            }
            for row in rows[:50]
        ]
        return out

    def run_scrap_price(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「废料月度销售价」#/scrap-price。"""
        tr = query.time_range
        rows = self._scrap_price_repo.query_rows(
            db,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
            location=query.location(),
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"废料价行={len(rows)}" if rows else "当前范围无废料销售价数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_scrap_price_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_scrap_price_drivers(rows)
        out.result = compose_result(parts_result, default_kind="summary")
        out.evidence["scrap_price_rows"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "location": row.location,
                "net_price": f"{row.net_price:.2f}",
                "market_price": f"{row.market_price:.2f}",
            }
            for row in rows[:50]
        ]
        return out

    def run_steel(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        tr = query.time_range
        location = query.location()
        steel_rows = self._steel_repo.query_monthly_avg(
            db,
            location=location,
            start_year=tr.start_year,
            start_month=tr.start_month,
            end_year=tr.end_year,
            end_month=tr.end_month,
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(steel_rows),
            data_message=f"钢材月度均价点数={len(steel_rows)}",
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_steel_summary(steel_rows)
        if "trend" in query.analyses:
            parts_result["trend"] = build_steel_trend(steel_rows, basis=query.comparison_basis)
        default_kind = "trend" if "trend" in query.analyses else "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        out.evidence["steel_series"] = [
            {
                "month": f"{row.year:04d}-{row.month:02d}",
                "avg_final_price": str(row.avg_final_price),
                "row_count": row.row_count,
            }
            for row in steel_rows
        ]
        return out
