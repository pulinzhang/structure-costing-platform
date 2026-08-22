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
_RANGE_RE = re.compile(
    r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*[到至\-~～]\s*(?:(\d{4})\s*年\s*)?(\d{1,2})\s*月"
)
_SINGLE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月")
_HALF_YEAR_RE = re.compile(r"过去\s*半年|近\s*半年")
_THIS_YEAR_RE = re.compile(r"今年以来|本年以来|今年")


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
        start = explicit_start if len(explicit_start) == 7 else month_key(
            int(explicit_start[:4]), int(explicit_start.split("-")[-1])
        )
        end = explicit_end if len(explicit_end) == 7 else month_key(
            int(explicit_end[:4]), int(explicit_end.split("-")[-1])
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

    if _HALF_YEAR_RE.search(text):
        start_year, start_month = shift_month(default.year, default.month, -5)
        return TimeRange(
            start=month_key(start_year, start_month),
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
        start_year, start_month = shift_month(
            default.year, default.month, -(count - 1)
        )
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
