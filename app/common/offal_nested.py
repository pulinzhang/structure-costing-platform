"""从工艺确认表「料片式样」拆出是否利废。

只认「利用…废料」短语；不用空长宽当利废。模具布点不走这里。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_OFFAL_PHRASE_RE = re.compile(r"利用\s*(.*?)\s*废料")
_SEPARATOR_RE = re.compile(r"[\s/／、,，;；]+")


@dataclass(frozen=True, slots=True)
class OffalSheetParse:
    """料片式样拆分结果。"""

    is_offal_nested: bool
    offal_source: str | None
    sheet_type: str | None


def parse_offal_from_sheet_type(raw: object) -> OffalSheetParse:
    """匹配「利用」+ 可选名称 +「废料」；剩余写入料片几何式样。"""
    if raw is None:
        return OffalSheetParse(False, None, None)
    text = str(raw).strip()
    if not text:
        return OffalSheetParse(False, None, None)

    match = _OFFAL_PHRASE_RE.search(text)
    if not match:
        return OffalSheetParse(False, None, text)

    source = (match.group(1) or "").strip() or None
    remainder_text = _OFFAL_PHRASE_RE.sub(" ", text)
    remainder: str | None = _SEPARATOR_RE.sub(" ", remainder_text).strip() or None
    return OffalSheetParse(True, source, remainder)
