"""组装本次 AnalysisSnapshot。"""

from __future__ import annotations

from app.common.timezone import now
from app.schemas.llm.analysis_query import AnalysisQuery
from app.schemas.llm.analysis_snapshot import AnalysisSnapshot, SnapshotMeta
from app.services.llm.action_builder import ActionBuilder
from app.services.llm.analysis.runner import AnalysisRunResult
from app.services.llm.query.comparison_basis import comparison_basis_label_zh


class SnapshotBuilder:
    def __init__(self) -> None:
        self._actions = ActionBuilder()

    def build(
        self,
        *,
        query: AnalysisQuery,
        run: AnalysisRunResult,
    ) -> AnalysisSnapshot:
        actions = self._actions.build(query=query, run=run)
        return AnalysisSnapshot(
            query=query,
            meta=SnapshotMeta(
                has_data=run.has_data,
                comparability=run.comparability,  # type: ignore[arg-type]
                comparison_basis_label=comparison_basis_label_zh(query.comparison_basis),
                generated_at=now().isoformat(),
                data_message=run.data_message,
                unresolved_mentions=list(query.unresolved_mentions),
            ),
            summary=run.summary,
            result=run.result,
            evidence=run.evidence,
            actions=actions,
        )
