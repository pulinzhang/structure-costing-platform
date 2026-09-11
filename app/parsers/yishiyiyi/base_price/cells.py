"""单元格取值：去空白、Decimal、规格。"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

_EMPTY_NUMBERS = ("-", "/", "#N/A", "#VALUE!", "None", "待商务发布")
_SPEC_RE = re.compile(r"([\d.]*[\d]+)\*(\d+)")


def cell_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def cell_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float):
        try:
            return Decimal(str(value))
        except Exception:
            return None
    text = str(value).strip()
    if not text or text in _EMPTY_NUMBERS:
        return None
    try:
        return Decimal(text)
    except Exception:
        return None


def parse_spec(spec_str: str) -> tuple[Decimal | None, Decimal | None]:
    """厚度*宽度；``.0*1250`` 视为 ``1.0*1250``。"""
    if not spec_str:
        return None, None
    match = _SPEC_RE.match(spec_str)
    if not match:
        return None, None
    thick_str = match.group(1)
    if thick_str.startswith("."):
        thick_str = "1" + thick_str
    return cell_decimal(thick_str), cell_decimal(match.group(2))
