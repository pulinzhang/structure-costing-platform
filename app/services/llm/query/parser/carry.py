"""上一问范围沿用：问句有证据才覆盖，缺槽才补。

改之前先对照测试名。不能破的约定：

1. 只信问句证据。LLM 草稿里没在问句出现的槽丢掉（防幻觉）。
2. 基地/项目/版本/对比基地：缺则补。零件号/吨位/政策：只有回指省略才粘。不按句长。「还有 / 还是 / 还原 / 应该 / 那么 / 哪怕 / 再次」里的单字不算回指。
3. 换基地且不是对比问 → 丢掉对比基地。换项目或整段新范围 → 丢掉版本和粘性槽。问哪些 / 那些 / 别的 / 其他，或问句自己点了零件以外的主题 → 丢掉问句里没出现的粘性槽。
4. 问句自带时间 = 整段新范围。钉表最新月时时间不沿用，零件号可以已经粘上。
5. subject 只在回指省略、且问句自己仍是 cost_total 时沿用。粘上的零件号把规则层落到裸 part 时，不把它当成换了主题。「呢」单独不是省略。
6. usage_help 不沿用。SCOPE_UNSET 不是真实范围。
"""

from __future__ import annotations

import re

from app.common.part_number import extract_part_number_from_text
from app.common.tonnage import extract_tonnage_from_text
from app.schemas.llm.analysis_query import SCOPE_UNSET, AnalysisQuery, TimeRange
from app.services.llm.query.parser.analyses import question_has_compare_signal
from app.services.llm.query.parser.subjects import resolve_subject
from app.services.llm.query.time_range import question_has_explicit_time

# 回指才粘零件。单字不能打在「还有 / 应该 / 那么 / 再次」里面。
_ELLIPSIS_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"贵在哪"),
    re.compile(r"这个(?!月)"),
    re.compile(r"它"),
    re.compile(r"(?<!应)该"),
    re.compile(r"^那(?!么|怕)"),
    re.compile(r"再(?!次)"),
    re.compile(r"还(?!有|是|原)"),
)
_RELEASE_PART_WORDS: tuple[str, ...] = (
    "总体",
    "汇总",
    "一览",
    "采购成本",
    "哪些",
    "那些",
    "别的",
    "其他",
    "其它",
    "其余",
)
_THIS_PART_WORDS: tuple[str, ...] = ("这个零件", "该零件", "此零件")
# 这些主题沿用零件号才有意义。问句自己点了别的主题时，粘性槽会把答案收成上一件。
_PART_SCOPED_SUBJECTS: frozenset[str] = frozenset(
    {
        "cost_total",
        "part",
        "l0",
        "stamping_part",
        "stamping_process",
        "stamping_process_fee",
    }
)
_SCOPE_KEYS: tuple[str, ...] = (
    "location",
    "vehicle_model",
    "bom_version",
    "compare_locations",
)
_STICKY_KEYS: tuple[str, ...] = ("part_number", "tonnage", "policy_type")
_BOM_VERSION_RE = re.compile(r"V\d+", re.IGNORECASE)
_DEFAULT_SUBJECT = "cost_total"
_PART_EXISTENCE_WORDS: tuple[str, ...] = ("存在", "有没有", "在不在", "在吗")


def should_carry_previous(previous: AnalysisQuery | None) -> bool:
    return previous is not None and previous.query_mode != "usage_help"


def is_full_new_scope(question: str, evidenced: dict[str, str]) -> bool:
    if question_has_explicit_time(question):
        return True
    return bool(evidenced.get("location") and evidenced.get("vehicle_model"))


def is_ellipsis_followup(question: str, *, is_full_new_scope_flag: bool) -> bool:
    """回指（那青岛呢 / 这个多少钱 / 贵在哪）。整段新范围时强制 False。不按句长。"""
    if is_full_new_scope_flag:
        return False
    text = (question or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _ELLIPSIS_RES)


def _value_in_question(question: str, value: str) -> bool:
    text = question or ""
    raw = (value or "").strip()
    if not raw:
        return False
    if raw in text:
        return True
    stripped = (
        raw.replace("基地", "").replace("厂", "").replace("车型", "").replace("项目", "").strip()
    )
    return len(stripped) >= 2 and stripped in text


def filter_key_evidenced(question: str, key: str, value: str) -> bool:
    if key == "part_number":
        return extract_part_number_from_text(question) is not None
    if key == "tonnage":
        return extract_tonnage_from_text(question) is not None
    if key == "compare_locations":
        return question_has_compare_signal(question)
    if key == "policy_type":
        return any(word in question for word in ("厚度", "宽度", "锌层"))
    if key == "bom_version":
        if _BOM_VERSION_RE.search(question or ""):
            return True
        return _value_in_question(question, value)
    return _value_in_question(question, value)


def keep_evidenced_filters(question: str, filters: dict[str, str]) -> dict[str, str]:
    """丢掉草稿里问句没有证据的槽；零件号/吨位以问句抽取为准。"""
    kept: dict[str, str] = {}
    for key, value in filters.items():
        if value and filter_key_evidenced(question, key, value):
            kept[key] = value
    part_token = extract_part_number_from_text(question)
    if part_token:
        kept["part_number"] = filters.get("part_number") or part_token
    tonnage_token = extract_tonnage_from_text(question)
    if tonnage_token is not None:
        kept["tonnage"] = str(tonnage_token)
    return kept


def merge_filters(
    *,
    question: str,
    current: dict[str, str],
    previous: AnalysisQuery,
) -> dict[str, str]:
    prev = {key: value for key, value in previous.filters.items() if value and value != SCOPE_UNSET}
    full_new = is_full_new_scope(question, current)
    ellipsis = is_ellipsis_followup(question, is_full_new_scope_flag=full_new)

    merged: dict[str, str] = {}
    for key in _SCOPE_KEYS:
        if key in prev:
            merged[key] = prev[key]
    if ellipsis:
        for key in _STICKY_KEYS:
            if key in prev:
                merged[key] = prev[key]

    merged.update(current)

    if (
        current.get("location")
        and current.get("location") != prev.get("location")
        and not question_has_compare_signal(question)
    ):
        merged.pop("compare_locations", None)

    vehicle_changed = bool(
        current.get("vehicle_model") and current.get("vehicle_model") != prev.get("vehicle_model")
    )
    if vehicle_changed or full_new:
        for key in ("bom_version", *_STICKY_KEYS):
            if key not in current:
                merged.pop(key, None)

    _drop_unstated_sticky(question, merged, current)

    return {key: value for key, value in merged.items() if value}


def _mentions_this_part(question: str) -> bool:
    return any(word in question for word in _THIS_PART_WORDS)


def _drop_unstated_sticky(
    question: str,
    merged: dict[str, str],
    current: dict[str, str],
) -> None:
    """问集合、或问句自己换了主题时，丢掉本句没写出的零件号/吨位/政策。"""
    release_part = any(word in question for word in _RELEASE_PART_WORDS)
    named_subject = resolve_subject(question=question, analyses=[], filters={})
    foreign_subject = named_subject not in _PART_SCOPED_SUBJECTS
    if not release_part and not foreign_subject:
        return
    for key in _STICKY_KEYS:
        if key in current:
            continue
        if key == "part_number" and _mentions_this_part(question):
            continue
        if key == "tonnage" and named_subject == "stamping_tonnage" and not release_part:
            continue
        merged.pop(key, None)


def apply_carried_filters(
    *,
    question: str,
    current: dict[str, str],
    previous: AnalysisQuery,
) -> tuple[dict[str, str], dict[str, str]]:
    evidenced = keep_evidenced_filters(question, current)
    return evidenced, merge_filters(
        question=question,
        current=evidenced,
        previous=previous,
    )


def resolve_carried_time(
    *,
    question: str,
    draft_time: TimeRange,
    previous: AnalysisQuery | None,
) -> tuple[TimeRange, str | None]:
    if question_has_explicit_time(question):
        return draft_time, None
    if not should_carry_previous(previous):
        return draft_time, None
    assert previous is not None
    prev = previous.time_range
    if prev.start == prev.end:
        message = f"沿用上一问时间 {prev.start_year}年{prev.start_month:02d}月"
    else:
        message = (
            f"沿用上一问时间 {prev.start_year}年{prev.start_month:02d}月"
            f"–{prev.end_year}年{prev.end_month:02d}月"
        )
    return prev, message


def resolve_carried_subject(
    *,
    question: str,
    resolved_subject: str,
    previous: AnalysisQuery | None,
    evidenced: dict[str, str],
) -> str:
    if not should_carry_previous(previous):
        return resolved_subject
    assert previous is not None
    if previous.query_mode != "analysis":
        return resolved_subject
    full_new = is_full_new_scope(question, evidenced)
    if not is_ellipsis_followup(question, is_full_new_scope_flag=full_new):
        return resolved_subject
    # 用问句自己的槽判断主题。粘上来的零件号会把规则层落到裸 part，那不是换主题。
    named = resolve_subject(question=question, analyses=[], filters=evidenced)
    if named != _DEFAULT_SUBJECT:
        return resolved_subject
    if resolved_subject == "part" and any(word in question for word in _PART_EXISTENCE_WORDS):
        return resolved_subject
    if resolved_subject not in {_DEFAULT_SUBJECT, "part"}:
        return resolved_subject
    return previous.subject
