"""加工费金额公共计算（CRUD 与计算共用）。"""

from __future__ import annotations

from decimal import Decimal

from app.common.money import Q3, optional_quantize_money

# 加工费量化步长（与 Numeric scale / 历史 import 名对齐）
FEE_QUANTIZE = Q3


def resolve_final_fee(
    processing_fee: Decimal | None,
    manual_unit_price: Decimal | None,
) -> Decimal | None:
    """最终加工费：有手工调整单价则用手工，否则用系统计算值。"""
    if manual_unit_price is not None:
        return optional_quantize_money(manual_unit_price, Q3)
    if processing_fee is None:
        return None
    return optional_quantize_money(processing_fee, Q3)
