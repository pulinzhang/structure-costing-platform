"""LLM 条件抽取草稿（LLM JSON → AnalysisQuery 之前）。"""

from __future__ import annotations

from typing import NotRequired

from typing_extensions import TypedDict


class ParserTimeRangeDraft(TypedDict, total=False):
    start: str
    end: str


class ParserDraft(TypedDict, total=False):
    """ConditionExtractor / rule_fallback 产出的条件草稿。"""

    time_range: ParserTimeRangeDraft
    filters: dict[str, object]
    compare_locations: list[object]
    subject: NotRequired[str]
    analyses: NotRequired[list[object]]
