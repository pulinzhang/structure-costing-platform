"""把 analyses 片段收成单一 result。"""

from __future__ import annotations

from app.schemas.llm.analysis_payload import (
    AnalysisResultLeafPayload,
    AnalysisResultPayload,
    CompositePayload,
    KindOnlyPayload,
)


def compose_result(
    parts_result: dict[str, AnalysisResultLeafPayload],
    *,
    default_kind: str,
) -> AnalysisResultPayload:
    if len(parts_result) == 1:
        return next(iter(parts_result.values()))
    if parts_result:
        composite: CompositePayload = {"kind": "composite", "parts": parts_result}
        return composite
    empty: KindOnlyPayload = {"kind": default_kind}
    return empty
