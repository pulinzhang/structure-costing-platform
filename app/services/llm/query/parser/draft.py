"""LLM 草稿回退与 time_range 解析。"""

from __future__ import annotations

from app.common.part_number import extract_part_number_from_text
from app.schemas.llm.analysis_query import TimeRange
from app.schemas.llm.parser_draft import ParserDraft
from app.services.llm.query.time_range import DefaultScopeMonth, normalize_time_range


def parse_time_range_from_draft(
    draft: ParserDraft,
    *,
    question: str,
    default: DefaultScopeMonth,
) -> TimeRange:
    raw = draft.get("time_range")
    start = None
    end = None
    if isinstance(raw, dict):
        start = str(raw.get("start") or "").strip() or None
        end = str(raw.get("end") or "").strip() or None
    return normalize_time_range(
        user_question=question,
        default=default,
        explicit_start=start,
        explicit_end=end,
    )


def rule_fallback_draft(
    question: str,
    default: DefaultScopeMonth,
) -> ParserDraft:
    """LLM 不可用：仅抽 time_range + filters。"""
    tr = normalize_time_range(user_question=question, default=default)
    filters: dict[str, object] = {}
    for known in ("青岛", "芜湖", "大连", "鄂尔多斯"):
        if known in question:
            filters["location"] = known
            break
    part_token = extract_part_number_from_text(question)
    if part_token:
        filters["part_number"] = part_token

    return {
        "time_range": {"start": tr.start, "end": tr.end},
        "filters": filters,
        "compare_locations": [],
    }
