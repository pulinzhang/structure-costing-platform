"""Pack 构建辅助：金额字符串化 / 上月 scope。"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping

from app.common.money import Q4


def money_str(value: object) -> str:
    if value is None:
        return "0.0000"
    if isinstance(value, Decimal):
        number = value
    else:
        number = Decimal(str(value))
    return f"{number.quantize(Q4, rounding=ROUND_HALF_UP):.4f}"


def decimal_sum(values: list[Decimal]) -> Decimal:
    total = Decimal("0")
    for value in values:
        total += value
    return total


def previous_month(year: int, month: int) -> tuple[int, int]:
    if month <= 1:
        return year - 1, 12
    return year, month - 1


def vo_dump(vo: object) -> dict[str, object]:
    """Pydantic VO → JSON 友好 dict（金额已是字符串）。"""
    dump = getattr(vo, "model_dump", None)
    if callable(dump):
        data = dump(mode="json")
        if isinstance(data, dict):
            return data
    return {}


def pick(mapping: Mapping[str, object], keys: set[str]) -> dict[str, object]:
    return {key: mapping[key] for key in keys if key in mapping}
