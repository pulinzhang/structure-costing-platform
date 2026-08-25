"""时间范围归一化。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.llm.analysis_query import TimeRange
from app.services.llm._money import month_key

_CN_NUM = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

_RECENT_MONTHS_RE = re.compile(r"近\s*([一二三四五六七八九十\d]+)\s*个?月")
_YEAR_FIRST_N_MONTHS_RE = re.compile(r"(\d{4})\s*年\s*前\s*([一二三四五六七八九十\d]+)\s*个?月")
_YEAR_ONLY_RE = re.compile(r"(\d{4})\s*年(?!\s*\d{1,2}\s*月)")
_RANGE_RE = re.compile(
    r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*[到至\-~～]\s*(?:(\d{4})\s*年\s*)?(\d{1,2})\s*月"
)
_SINGLE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月")
_HALF_YEAR_RE = re.compile(r"过去\s*半年|近\s*半年")
_THIS_YEAR_RE = re.compile(r"今年以来|本年以来|今年(?![与和].*去年)")
_YOY_RE = re.compile(r"今年与去年|去年和今年|去年与今年|同比")


def _parse_cn_or_int(text: str) -> int:
    text = text.strip()
    if text.isdigit():
        return int(text)
    return _CN_NUM.get(text, 1)


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


@dataclass(frozen=True, slots=True)
class DefaultScopeMonth:
    year: int
    month: int


def normalize_time_range(
    *,
    user_question: str,
    default: DefaultScopeMonth,
    explicit_start: str | None = None,
    explicit_end: str | None = None,
) -> TimeRange:
    if explicit_start and explicit_end:
        start = (
            explicit_start
            if len(explicit_start) == 7
            else month_key(int(explicit_start[:4]), int(explicit_start.split("-")[-1]))
        )
        end = (
            explicit_end
            if len(explicit_end) == 7
            else month_key(int(explicit_end[:4]), int(explicit_end.split("-")[-1]))
        )
        if start > end:
            start, end = end, start
        return TimeRange(start=start, end=end)

    text = user_question or ""

    range_match = _RANGE_RE.search(text)
    if range_match:
        start_year = int(range_match.group(1))
        start_month = int(range_match.group(2))
        end_year = int(range_match.group(3) or start_year)
        end_month = int(range_match.group(4))
        start = month_key(start_year, start_month)
        end = month_key(end_year, end_month)
        if start > end:
            start, end = end, start
        return TimeRange(start=start, end=end)

    year_first = _YEAR_FIRST_N_MONTHS_RE.search(text)
    if year_first:
        year = int(year_first.group(1))
        count = min(12, max(1, _parse_cn_or_int(year_first.group(2))))
        return TimeRange(
            start=month_key(year, 1),
            end=month_key(year, count),
        )

    year_only = _YEAR_ONLY_RE.search(text)
    if year_only:
        year = int(year_only.group(1))
        return TimeRange(
            start=month_key(year, 1),
            end=month_key(year, 12),
        )

    if _HALF_YEAR_RE.search(text):
        start_year, start_month = shift_month(default.year, default.month, -5)
        return TimeRange(
            start=month_key(start_year, start_month),
            end=month_key(default.year, default.month),
        )

    if _YOY_RE.search(text):
        return TimeRange(
            start=month_key(default.year - 1, 1),
            end=month_key(default.year, default.month),
        )

    if _THIS_YEAR_RE.search(text):
        return TimeRange(
            start=month_key(default.year, 1),
            end=month_key(default.year, default.month),
        )

    recent = _RECENT_MONTHS_RE.search(text)
    if recent:
        count = max(1, _parse_cn_or_int(recent.group(1)))
        start_year, start_month = shift_month(default.year, default.month, -(count - 1))
        return TimeRange(
            start=month_key(start_year, start_month),
            end=month_key(default.year, default.month),
        )

    single = _SINGLE_RE.search(text)
    if single:
        year = int(single.group(1))
        month = int(single.group(2))
        key = month_key(year, month)
        return TimeRange(start=key, end=key)

    key = month_key(default.year, default.month)
    return TimeRange(start=key, end=key)


def question_has_explicit_time(user_question: str) -> bool:
    """问句是否包含可识别的时间表达（用于 C.4.2.1 第 3 级判定）。"""
    text = user_question or ""
    if _RANGE_RE.search(text):
        return True
    if _YEAR_FIRST_N_MONTHS_RE.search(text):
        return True
    if _YEAR_ONLY_RE.search(text):
        return True
    if _HALF_YEAR_RE.search(text):
        return True
    if _YOY_RE.search(text):
        return True
    if _THIS_YEAR_RE.search(text):
        return True
    if _RECENT_MONTHS_RE.search(text):
        return True
    return bool(_SINGLE_RE.search(text))


def draft_has_time_range(draft: dict[str, object]) -> bool:
    raw = draft.get("time_range")
    if not isinstance(raw, dict):
        return False
    start = str(raw.get("start") or "").strip()
    end = str(raw.get("end") or "").strip()
    return bool(start and end)


def count_months_in_span(start: str, end: str) -> int:
    """闭区间 YYYY-MM 包含的月份数。"""
    start_key = (start or "").strip()[:7]
    end_key = (end or "").strip()[:7]
    if len(start_key) != 7 or len(end_key) != 7:
        return 0
    start_year, start_month = int(start_key[:4]), int(start_key[5:7])
    end_year, end_month = int(end_key[:4]), int(end_key[5:7])
    if start_key > end_key:
        start_year, start_month, end_year, end_month = (
            end_year,
            end_month,
            start_year,
            start_month,
        )
    return (end_year - start_year) * 12 + (end_month - start_month) + 1
