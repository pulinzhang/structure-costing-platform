"""作业台 / 模具费 / 检具费 / 采购对象。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.llm.die_fee_analysis_repository import DieFeeAnalysisRepository
from app.repositories.llm.gauge_fee_analysis_repository import GaugeFeeAnalysisRepository
from app.repositories.llm.ops_workbench_repository import OpsWorkbenchRepository
from app.repositories.llm.procurement_object_analysis_repository import (
    ProcurementObjectAnalysisRepository,
)
from app.schemas.llm.analysis_payload import (
    AnalysisResultLeafPayload,
    RiskEntry,
)
from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm.analysis.ops.masterdata import (
    build_die_fee_drilldown,
    build_die_fee_summary,
    build_gauge_fee_drilldown,
    build_gauge_fee_summary,
    build_procurement_object_drilldown,
    build_procurement_object_summary,
)
from app.services.llm.analysis.ops.workbench import (
    build_ops_workbench_risks,
    build_ops_workbench_summary,
)
from app.services.llm.analysis.shared.compose import compose_result
from app.services.llm.analysis.shared.result import AnalysisRunResult
from app.services.llm.comparison_basis import resolve_comparability


class OpsAnalysis:
    def __init__(self) -> None:
        self._ops_workbench_repo = OpsWorkbenchRepository()
        self._die_fee_repo = DieFeeAnalysisRepository()
        self._gauge_fee_repo = GaugeFeeAnalysisRepository()
        self._procurement_object_repo = ProcurementObjectAnalysisRepository()

    def run_ops_workbench(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        tr = query.time_range
        boards = self._ops_workbench_repo.query_boards(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            year=tr.end_year,
            month=tr.end_month,
        )
        summary = build_ops_workbench_summary(boards)
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=any(row.row_count > 0 for row in boards),
            data_message=(
                f"待审核={summary['pending_audit_total']}，"
                f"未完成={summary['incomplete_total']}，"
                f"待确认外发={summary['pending_confirm_total']}"
            ),
            summary=summary,
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "risk" in query.analyses:
            parts_result["risk"] = build_ops_workbench_risks(summary)
        out.result = compose_result(parts_result, default_kind="summary")
        return out

    def run_stamping_die_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        tr = query.time_range
        part_token = query.part_number() or ""
        rows = self._die_fee_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            start_year=tr.start_year,
            end_year=tr.end_year,
            part_number=part_token or None,
        )
        head = self._die_fee_repo.pick_best_row(rows, part_token=part_token) if part_token else None
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"模具费行={len(rows)}" if rows else "当前范围无模具费数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_die_fee_summary(rows)
        if "risk" in query.analyses and out.summary:
            pending = int(str(out.summary.get("pending_audit_count") or 0))
            zero = int(str(out.summary.get("zero_fee_count") or 0))
            risks: list[RiskEntry] = []
            if pending:
                risks.append(
                    {
                        "risk_type": "pending_audit",
                        "count": pending,
                        "message": "尚有模具费未审核",
                    }
                )
            if zero:
                risks.append(
                    {
                        "risk_type": "zero_fee",
                        "count": zero,
                        "message": "尚有模具费为 0",
                    }
                )
            parts_result["risk"] = {"kind": "risk", "risks": risks}
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_die_fee_drilldown(
                rows, part_token=part_token, head=head
            )
        default_kind = "drilldown" if part_token else "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        return out

    def run_stamping_gauge_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        part_token = query.part_number() or ""
        rows = self._gauge_fee_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            part_number=part_token or None,
        )
        head = (
            self._gauge_fee_repo.pick_best_row(rows, part_token=part_token) if part_token else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"检具费行={len(rows)}" if rows else "当前范围无检具费档案"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_gauge_fee_summary(rows)
        if "risk" in query.analyses and out.summary:
            zero = int(str(out.summary.get("zero_fee_count") or 0))
            invalid = int(str(out.summary.get("invalid_count") or 0))
            gauge_risks: list[RiskEntry] = []
            if zero:
                gauge_risks.append(
                    {
                        "risk_type": "zero_fee",
                        "count": zero,
                        "message": "尚有检具费为 0",
                    }
                )
            if invalid:
                gauge_risks.append(
                    {
                        "risk_type": "invalid_gauge",
                        "count": invalid,
                        "message": "尚有检具费档案非有效",
                    }
                )
            parts_result["risk"] = {"kind": "risk", "risks": gauge_risks}
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_gauge_fee_drilldown(
                rows, part_token=part_token, head=head
            )
        default_kind = "drilldown" if part_token else "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        return out

    def run_procurement_object(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        part_token = query.part_number() or ""
        rows = self._procurement_object_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
            part_number=part_token or None,
        )
        head = (
            self._procurement_object_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"采购对象行={len(rows)}" if rows else "当前范围无采购对象清单"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_procurement_object_summary(rows)
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_procurement_object_drilldown(
                rows, part_token=part_token, head=head
            )
        if "risk" in query.analyses and out.summary:
            pending_confirm = int(str(out.summary.get("pending_confirm_count") or 0))
            pending_audit = int(str(out.summary.get("pending_audit_count") or 0))
            anomaly = int(str(out.summary.get("anomaly_count") or 0))
            risks: list[RiskEntry] = []
            if pending_confirm:
                risks.append(
                    {
                        "risk_type": "pending_confirm",
                        "count": pending_confirm,
                        "message": "尚有采购对象未确认外发/自制",
                    }
                )
            if pending_audit:
                risks.append(
                    {
                        "risk_type": "pending_audit",
                        "count": pending_audit,
                        "message": "尚有采购对象未审核",
                    }
                )
            if anomaly:
                risks.append(
                    {
                        "risk_type": "procurement_anomaly",
                        "count": anomaly,
                        "message": "采购对象核对区仍有异常件",
                    }
                )
            parts_result["risk"] = {"kind": "risk", "risks": risks}
        default_kind = "drilldown" if part_token else "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        return out
