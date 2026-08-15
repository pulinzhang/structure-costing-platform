"""加工费金额公共计算（CRUD 与计算共用）。"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

FEE_QUANTIZE = Decimal("0.001")


def resolve_final_fee(
    processing_fee: Decimal | float | None,
    manual_unit_price: Decimal | float | None,
) -> Decimal | None:
    """最终加工费：有手工调整单价则用手工，否则用系统计算值。"""
    if manual_unit_price is not None:
        return Decimal(str(manual_unit_price)).quantize(
            FEE_QUANTIZE, rounding=ROUND_HALF_UP
        )
    if processing_fee is None:
        return None
    return Decimal(str(processing_fee)).quantize(
        FEE_QUANTIZE, rounding=ROUND_HALF_UP
    )
