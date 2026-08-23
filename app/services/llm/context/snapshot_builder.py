"""组装本次 AnalysisSnapshot。"""

from __future__ import annotations

from app.common.timezone import now
from app.schemas.llm.analysis_query import AnalysisQuery
from app.schemas.llm.analysis_snapshot import AnalysisSnapshot, SnapshotMeta
from app.services.llm.analysis.constants import ANALYSIS_VERSION
from app.services.llm.analysis.runner import AnalysisRunResult
from app.services.llm.query.comparison_basis import comparison_basis_label_zh


class SnapshotBuilder:
    def build(
        self,
        *,
        query: AnalysisQuery,
        run: AnalysisRunResult,
    ) -> AnalysisSnapshot:
        data_message = run.data_message or query.parser_data_message
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
            ),
            summary=run.summary,
            result=run.result,
            evidence=run.evidence,
        )
