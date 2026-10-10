"""金额与年月工具（切片叶模块；query / analysis / repo 可向下依赖）。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

_MONEY_QUANT = Decimal("0.01")
_RATE_QUANT = Decimal("0.01")


def money_str(value: Decimal | int | float | None) -> str:
    """B.6.1：金额保留 2 位小数。"""
    if value is None:
        return "0.00"
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    quantized = number.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def rate_str(value: Decimal | int | float | None) -> str:
    """B.6.1：涨幅比率保留 2 位小数（小数形式，如 0.15 = 15%）。"""
    if value is None:
        return "0.00"
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    quantized = number.quantize(_RATE_QUANT, rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def ym_int(year: int, month: int) -> int:
    return year * 100 + month


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


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
