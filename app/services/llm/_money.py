"""金额与年月工具（分析切片内部）。"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

_MONEY_QUANT = Decimal("0.0001")


def money_str(value: Decimal | int | float | None) -> str:
    if value is None:
        return "0.0000"
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    quantized = number.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def parse_month_key(value: str) -> tuple[int, int]:
    year_text, month_text = value.split("-", 1)
    return int(year_text), int(month_text)


def ym_int(year: int, month: int) -> int:
    return year * 100 + month
