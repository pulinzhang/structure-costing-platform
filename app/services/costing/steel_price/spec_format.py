"""厚度 / 宽度 / 规格展示格式（导出与计算落库共用）。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip()
    if not text:
        return None
    return Decimal(text)


def format_thickness(value: Any) -> str:
    """
    厚度展示：至少一位小数，去掉多余尾零。

    例：1 → 1.0，0.70 → 0.7，0.65 → 0.65，1.50 → 1.5
    """
    number = _to_decimal(value)
    if number is None:
        return ""
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if "." not in text:
        text = f"{text}.0"
    return text


def format_width(value: Any) -> str:
    """宽度展示：整数不带小数；非整数去掉尾零。"""
    number = _to_decimal(value)
    if number is None:
        return ""
    if number == number.to_integral_value():
        return str(int(number))
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def build_spec(thickness: Any, width: Any) -> str:
    """规格：{厚度}*{宽度}，如 0.7*1250、1.0*1250。"""
    thickness_text = format_thickness(thickness)
    width_text = format_width(width)
    if not thickness_text or not width_text:
        return ""
    return f"{thickness_text}*{width_text}"
