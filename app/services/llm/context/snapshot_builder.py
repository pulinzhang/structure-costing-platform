"""组装本次 AnalysisSnapshot。"""

from __future__ import annotations

from app.common.timezone import now
from app.schemas.llm.analysis_query import AnalysisQuery
from app.schemas.llm.analysis_snapshot import AnalysisSnapshot, SnapshotMeta, SnapshotScope
from app.services.llm.analysis.runner import AnalysisRunResult
from app.services.llm.analysis.shared.constants import ANALYSIS_VERSION
from app.services.llm.query.comparison_basis import comparison_basis_label_zh
from app.services.llm.query.time_range import count_months_in_span


def _month_count_with_data(run: AnalysisRunResult) -> int:
    summary = run.summary or {}
    months = summary.get("months")
    if isinstance(months, list) and months:
        return len(months)
    month_count = summary.get("month_count")
    if isinstance(month_count, int) and month_count > 0:
        return month_count
    evidence = run.evidence or {}
    monthly_totals = evidence.get("monthly_totals")
    if isinstance(monthly_totals, list) and monthly_totals:
        return len(monthly_totals)
    return 0


def _build_scope(query: AnalysisQuery, run: AnalysisRunResult) -> SnapshotScope:
    start = query.time_range.start
    end = query.time_range.end
    month_count = _month_count_with_data(run)
    query_month_span = count_months_in_span(start, end)
    is_full_calendar_year = (
        start[:4] == end[:4]
        and start.endswith("-01")
        and end.endswith("-12")
        and month_count >= 12
        and query_month_span >= 12
    )
    has_coverage_gap = query_month_span > 0 and month_count < query_month_span
    return SnapshotScope(
        time_range={"start": start, "end": end},
        year=int(end[:4]) if len(end) >= 7 else None,
        month=int(end[5:7]) if len(end) >= 7 else None,
        month_count=month_count,
        query_month_span=query_month_span,
        is_full_calendar_year=is_full_calendar_year,
        has_coverage_gap=has_coverage_gap,
    )


class SnapshotBuilder:
    def build(
        self,
        *,
        query: AnalysisQuery,
        run: AnalysisRunResult,
    ) -> AnalysisSnapshot:
        data_message = run.data_message or query.parser_data_message
        scope = _build_scope(query, run)
        return AnalysisSnapshot(
            query=query,
            meta=SnapshotMeta(
                has_data=run.has_data,
                comparability=run.comparability,  # type: ignore[arg-type]
                comparison_basis_label=comparison_basis_label_zh(query.comparison_basis),
                generated_at=now().isoformat(),
                data_message=data_message,
                unresolved_mentions=list(query.unresolved_mentions),
                anomaly_note=run.anomaly_note,
                analysis_version=run.analysis_version or ANALYSIS_VERSION,
                trace_id=query.trace_id,
                comparability_note=run.comparability_note,
                filtered_missing_price_count=run.filtered_missing_price_count,
                scope=scope,
            ),
            summary=run.summary,
            result=run.result,
            evidence=run.evidence,
        )
