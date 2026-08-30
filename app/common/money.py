"""
金额 / 单价 / 费用 / 费率：Decimal 量化与字符串序列化。

业务层禁止长期持有 float；JSON 金额字段输出固定小数位字符串。
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# 常用量化步长（与各表 Numeric scale 对齐）
Q0 = Decimal("1")
Q2 = Decimal("0.01")
Q3 = Decimal("0.001")
Q4 = Decimal("0.0001")
Q6 = Decimal("0.000001")


def parse_decimal(value: Any) -> Decimal:
    """任意入参 → Decimal；JSON float 必须经 str 转回。"""
    if value is None:
        raise ValueError("数值不能为空")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise ValueError("布尔值不是有效数值")
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            raise ValueError("数值不能为空")
        return Decimal(text)
    return Decimal(str(value))


def quantize_money(
    value: Any,
    quant: str | Decimal,
    *,
    allow_negative: bool = False,
) -> Decimal:
    """量化为指定小数位；默认不允许负数。"""
    number = parse_decimal(value)
    if not allow_negative and number < 0:
        raise ValueError("数值不能为负")
    step = Decimal(quant) if isinstance(quant, str) else quant
    return number.quantize(step, rounding=ROUND_HALF_UP)


def quantize_positive_whole(value: Any, *, label: str = "数量") -> Decimal:
    """正整数（如分摊万台）。计算层仍用 Decimal，禁止小数。"""
    number = parse_decimal(value)
    if number <= 0:
        raise ValueError(f"{label}须为正整数")
    quantized = number.quantize(Q0, rounding=ROUND_HALF_UP)
    if quantized != number:
        raise ValueError(f"{label}须为正整数")
    return quantized


def optional_quantize_money(
    value: Any,
    quant: str | Decimal,
    *,
    allow_negative: bool = False,
) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return quantize_money(value, quant, allow_negative=allow_negative)


def format_money(
    value: Any,
    quant: str | Decimal,
    places: int,
    *,
    allow_negative: bool = True,
) -> str:
    """序列化为固定小数位字符串。"""
    if value is None:
        number = Decimal("0").quantize(
            Decimal(quant) if isinstance(quant, str) else quant,
            rounding=ROUND_HALF_UP,
        )
    else:
        number = quantize_money(value, quant, allow_negative=allow_negative)
    return f"{number:.{places}f}"


def optional_format_money(
    value: Any,
    quant: str | Decimal,
    places: int,
    *,
    allow_negative: bool = True,
) -> str | None:
    if value is None:
        return None
    return format_money(value, quant, places, allow_negative=allow_negative)


def excel_money_cell(
    value: Any,
    quant: str | Decimal,
    *,
    allow_negative: bool = True,
) -> Decimal | str:
    """Excel 写入：保持 Decimal，空则空串。"""
    if value is None:
        return ""
    return quantize_money(value, quant, allow_negative=allow_negative)
