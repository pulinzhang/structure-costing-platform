"""还原页金额：统一四位小数，比较也走同一量化。"""

from __future__ import annotations

from decimal import Decimal

from app.common.money import Q4, quantize_money


def _money(value: object | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return quantize_money(value, Q4, allow_negative=True)


def _opt_money(value: object | None) -> Decimal | None:
    if value is None:
        return None
    return quantize_money(value, Q4, allow_negative=True)


def _match(left: Decimal, right: Decimal) -> bool:
    return _money(left) == _money(right)
