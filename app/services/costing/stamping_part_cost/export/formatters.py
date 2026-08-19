"""导出用格式化工具。"""

from __future__ import annotations

from decimal import Decimal


def formula_number(value: Decimal) -> str:
    """写入公式的小数，去掉多余尾零。"""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
