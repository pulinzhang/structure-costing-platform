"""成品焊接费金额计算（CRUD 与计算共用）。"""

from __future__ import annotations

from decimal import Decimal

from app.common.money import Q4, optional_quantize_money


def resolve_final_l0_welding_fee(
    total_l0_welding_fee: Decimal | None,
    other_fee: Decimal | None = None,
) -> Decimal | None:
    """确认单价 = 系统计算焊接费 + 其它费用。"""
    other = other_fee if other_fee is not None else Decimal("0")
    if total_l0_welding_fee is None:
        if other == 0:
            return None
        return optional_quantize_money(other, Q4)
    return optional_quantize_money(total_l0_welding_fee + other, Q4)
