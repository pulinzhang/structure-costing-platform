"""从工艺确认表「料片式样」拆出是否利废。

规则（按顺序）：
1. 含「要利废」→ 废料产生者，不是利用件
2. 「利用…废料」→ 利用件，短语从式样里拆走
3. 含「利废」或「利费」→ 利用件（签字变体/错字），式样原文保留
不用空长宽当利废。模具布点不走这里。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_OFFAL_PHRASE_RE = re.compile(r"利用\s*(.*?)\s*废料")
_SEPARATOR_RE = re.compile(r"[\s/／、,，;；]+")
_GENERATOR_MARK = "要利废"
_UTILIZER_MARKS = ("利废", "利费")


@dataclass(frozen=True, slots=True)
class OffalSheetParse:
    """料片式样拆分结果。"""

    is_offal_nested: bool
    offal_source: str | None
    sheet_type: str | None


def parse_offal_from_sheet_type(raw: object) -> OffalSheetParse:
    if raw is None:
        return OffalSheetParse(False, None, None)
    text = str(raw).strip()
    if not text:
        return OffalSheetParse(False, None, None)

    if _GENERATOR_MARK in text:
        return OffalSheetParse(False, None, text)

    match = _OFFAL_PHRASE_RE.search(text)
    if match:
        source = (match.group(1) or "").strip() or None
        remainder_text = _OFFAL_PHRASE_RE.sub(" ", text)
        remainder: str | None = _SEPARATOR_RE.sub(" ", remainder_text).strip() or None
        return OffalSheetParse(True, source, remainder)

    if any(mark in text for mark in _UTILIZER_MARKS):
        return OffalSheetParse(True, None, text)

    return OffalSheetParse(False, None, text)
