"""导出用格式化工具。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def format_datetime(value: Any) -> Any:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S") if hasattr(value, "strftime") else str(value)


def formula_number(value: Decimal) -> str:
    """写入公式的小数，去掉多余尾零。"""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
