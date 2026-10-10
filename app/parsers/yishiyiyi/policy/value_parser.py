"""单元格值解析工具。

提供:
- _to_str: 单元格 → str（去除前后空白）
- _to_str_or_none: 单元格 → str | None（None 表示无值）
- _to_decimal: 数字 / 字符串 → Decimal
- _to_int_price: 加减价 → int
- is_carry_forward_price: 末档 ``/`` / ``无`` 是否沿用上一阶梯
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_DECIMAL_STRIP_CHARS = " \t\u3000元/吨件mm\t"
_ONE = Decimal("1")
# 厚度末档 Excel 约定：沿用上一阶梯加减价（不是 0）
_CARRY_FORWARD_PRICE_MARKERS = frozenset({"/", "／", "无"})


def _to_str(value: object) -> str:
    """单元格值转为字符串（已 strip）。"""
    if value is None:
        return ""
    return str(value).strip()


def _to_str_or_none(value: object) -> str | None:
    """单元格值转为 None 或字符串（已 strip）。"""
    text = _to_str(value)
    return text if text else None


def _to_decimal(value: object) -> Decimal | None:
    """单元格值 → Decimal。

    - None / 空白 / 不可解析 → None
    - 数字类型直接构造
    - 字符串先尝试解析，失败返回 None
    """
    if value is None:
        return None
    if isinstance(value, int | float | Decimal):
        return Decimal(str(value))
    text = _to_str(value)
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def is_carry_forward_price(value: object) -> bool:
    """厚度末档单元格是否表示「沿用上一阶梯」。

    Excel 常见填 ``/``、全角 ``／`` 或 ``无``；不能当 0 元/吨。
    """
    return _to_str(value) in _CARRY_FORWARD_PRICE_MARKERS


def _to_int_price(value: object) -> int:
    """加减价 → int（元/吨），四舍五入。

    - 不能解析为数字 → 0（末档 ``/`` / ``无`` 须在装配时沿用上一档，勿直接当 0）
    - 接受负号（减价），例如 "-30"
    - Excel 公式残留小数（如 203.5398...）按 ROUND_HALF_UP 取整
    """
    dec = _to_decimal(value)
    if dec is None:
        return 0
    return int(dec.quantize(_ONE, rounding=ROUND_HALF_UP))
