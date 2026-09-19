"""焊接单价 / 工艺拆解 / 成品焊接费。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.llm.l0_welding_fee_analysis_repository import (
    L0WeldingFeeAnalysisRepository,
)
from app.repositories.llm.welding_process_breakdown_analysis_repository import (
    WeldingProcessBreakdownAnalysisRepository,
)
from app.repositories.llm.welding_unit_price_analysis_repository import (
    WeldingUnitPriceAnalysisRepository,
)
from app.schemas.llm.analysis_payload import (
    AnalysisResultLeafPayload,
)
from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm.analysis.shared.anomaly import build_welding_fee_risks
from app.services.llm.analysis.shared.compose import compose_result
from app.services.llm.analysis.shared.cost_driver import build_welding_fee_mom_anomalies
from app.services.llm.analysis.shared.result import AnalysisRunResult
from app.services.llm.analysis.welding.breakdown import (
    build_welding_breakdown_drilldown,
    build_welding_breakdown_drivers,
    build_welding_breakdown_summary,
)
from app.services.llm.analysis.welding.l0_fee import (
    build_l0_welding_fee_comparison,
    build_l0_welding_fee_drilldown,
    build_l0_welding_fee_drivers,
    build_l0_welding_fee_summary,
)
from app.services.llm.analysis.welding.unit_price import (
    build_welding_unit_price_comparison,
    build_welding_unit_price_drivers,
    build_welding_unit_price_summary,
)
from app.services.llm.comparison_basis import resolve_comparability


class WeldingAnalysis:
    def __init__(self) -> None:
        self._welding_unit_price_repo = WeldingUnitPriceAnalysisRepository()
        self._welding_breakdown_repo = WeldingProcessBreakdownAnalysisRepository()
        self._l0_welding_fee_repo = L0WeldingFeeAnalysisRepository()

    def run_welding_unit_price(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「焊接单价列表」#/bom-welding-unit-price。"""
        tr = query.time_range
        rows = self._welding_unit_price_repo.query_rows(
            db,
            location=query.location(),
            start_year=tr.start_year,
            end_year=tr.end_year,
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"焊接单价行={len(rows)}" if rows else "当前范围无焊接单价数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}

        if "summary" in query.analyses:
            out.summary = build_welding_unit_price_summary(rows)

        if "comparison" in query.analyses:
            parts_result["comparison"] = build_welding_unit_price_comparison(
                rows,
                location=query.location(),
            )

        if "drivers" in query.analyses:
            parts_result["drivers"] = build_welding_unit_price_drivers(rows)

        default_kind = "comparison" if "comparison" in query.analyses else "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        out.evidence["welding_unit_price_rows"] = [
            {
                "year": row.year,
                "location": row.location,
                "item_name": row.item_name,
                "unit": row.unit,
                "unit_price": f"{row.unit_price:.4f}",
                "audit_status": row.audit_status,
            }
            for row in rows[:50]
        ]
        return out

    def run_welding_process_breakdown(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「焊接工艺拆解列表」#/bom-welding-process-breakdown-list。"""
        part_token = query.part_number() or ""
        rows = self._welding_breakdown_repo.query_node_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
            part_number=part_token or None,
        )
        head = (
            self._welding_breakdown_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(
                f"焊接工艺拆解节点={len(rows)}" if rows else "当前范围无焊接工艺拆解数据"
            ),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_welding_breakdown_summary(rows)
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_welding_breakdown_drivers(rows)
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_welding_breakdown_drilldown(
                rows,
                part_token=part_token,
                head=head,
            )
        default_kind = "drilldown" if part_token else "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        out.evidence["welding_breakdown_rows"] = [
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "process_line_count": row.process_line_count,
                "location": row.location,
                "vehicle_model": row.vehicle_model,
                "bom_version": row.bom_version,
            }
            for row in rows[:50]
        ]
        return out

    def run_l0_welding_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        """对齐「焊接费列表」#/bom-welding-fee-list。"""
        tr = query.time_range
        part_token = query.part_number() or ""
        peek_previous_year = tr.start_year == tr.end_year and any(
            kind in query.analyses for kind in ("risk", "drivers", "trend", "comparison")
        )
        start_year = tr.start_year - 1 if peek_previous_year else tr.start_year
        rows = self._l0_welding_fee_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
            start_year=start_year,
            end_year=tr.end_year,
            part_number=part_token or None,
        )
        if not rows and part_token:
            rows = self._l0_welding_fee_repo.query_rows(
                db,
                location=query.location(),
                vehicle_model=query.vehicle_model(),
                bom_version=query.bom_version(),
                part_number=part_token,
            )
        focus_rows = (
            [row for row in rows if row.year == tr.end_year] if peek_previous_year else rows
        )
        head = (
            self._l0_welding_fee_repo.pick_best_row(focus_rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(focus_rows),
            data_message=(
                f"成品焊接费行={len(focus_rows)}" if focus_rows else "当前范围无成品焊接费数据"
            ),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_l0_welding_fee_summary(focus_rows)
        if "comparison" in query.analyses:
            parts_result["comparison"] = build_l0_welding_fee_comparison(
                rows,
                location=query.location(),
            )
        if "drivers" in query.analyses:
            parts_result["drivers"] = build_l0_welding_fee_drivers(rows)
        if "risk" in query.analyses:
            parts_result["risk"] = build_welding_fee_risks(focus_rows)
        if rows and any(kind in query.analyses for kind in ("risk", "drivers", "trend")):
            parts_result["mom_anomalies"] = build_welding_fee_mom_anomalies(
                rows,
                focus_year=tr.end_year if peek_previous_year else None,
            )
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_l0_welding_fee_drilldown(
                focus_rows,
                part_token=part_token,
                head=head,
            )
        if "comparison" in query.analyses:
            default_kind = "comparison"
        elif part_token:
            default_kind = "drilldown"
        else:
            default_kind = "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        out.evidence["l0_welding_fee_rows"] = [
            {
                "year": row.year,
                "part_number": row.part_number,
                "part_name": row.part_name,
                "final_l0_welding_fee": (
                    f"{(row.final_l0_welding_fee or row.total_l0_welding_fee):.4f}"
                ),
                "calc_status": row.calc_status,
            }
            for row in focus_rows[:50]
        ]
        return out
