"""单元格值解析工具。

提供:
- _to_str: 单元格 → str（去除前后空白）
- _to_str_or_none: 单元格 → str | None（None 表示无值）
- _to_decimal: 数字 / 字符串 → Decimal
- _to_int_price: 加减价 → int
- is_decimal_like: 判断字符串是否可解析为数字
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Optional

_DECIMAL_STRIP_CHARS = " \t\u3000元/吨件mm\t"


def _to_str(value: Any) -> str:
    """单元格值转为字符串（已 strip）。"""
    if value is None:
        return ""
    return str(value).strip()


def _to_str_or_none(value: Any) -> Optional[str]:
    """单元格值转为 None 或字符串（已 strip）。"""
    text = _to_str(value)
    return text if text else None


def is_decimal_like(text: str) -> bool:
    """判断字符串能否被解析为 Decimal。"""
    if not text:
        return False
    cleaned = text.strip().lstrip("+-")
    if not cleaned:
        return False
    try:
        Decimal(cleaned)
        return True
    except (InvalidOperation, ValueError):
        return False


def _to_decimal(value: Any) -> Optional[Decimal]:
    """单元格值 → Decimal。

    - None / 空白 / 不可解析 → None
    - 数字类型直接构造
    - 字符串先尝试解析，失败返回 None
    """
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = _to_str(value)
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _to_int_price(value: Any) -> int:
    """加减价 → int（元/吨）。

    - 不能解析为数字 → 0
    - 接受负号（减价），例如 "-30"
    """
    dec = _to_decimal(value)
    if dec is None:
        return 0
    return int(dec)
