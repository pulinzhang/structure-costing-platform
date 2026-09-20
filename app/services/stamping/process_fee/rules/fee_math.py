"""加工费金额公共计算（CRUD 与计算共用）。"""

from __future__ import annotations

from decimal import Decimal

from app.common.money import Q3, optional_quantize_money

# 加工费量化步长（与 Numeric scale / 历史 import 名对齐）
FEE_QUANTIZE = Q3


def resolve_final_fee(
    processing_fee: Decimal | None,
    other_fee: Decimal | None = None,
) -> Decimal | None:
    """确认单价 = 系统计算加工费 + 其它费用。"""
    other = other_fee if other_fee is not None else Decimal("0")
    if processing_fee is None:
        if other == 0:
            return None
        return optional_quantize_money(other, Q3)
    return optional_quantize_money(processing_fee + other, Q3)
