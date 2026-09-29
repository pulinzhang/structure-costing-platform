"""摆剪判定（工艺导入落主表、加工费计 0、零件核价快照共用）。"""

from __future__ import annotations

from decimal import Decimal

from app.common.measures import KG_PER_TON

SWING_SHEAR_MARK = "摆剪"


def contains_swing_shear(*values: object) -> bool:
    """任一文本含「摆剪」（含摆剪机、摆剪（28°）等）。"""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and SWING_SHEAR_MARK in text:
            return True
    return False


def is_swing_shear_label(process_code: str | None, process_seq: str | None) -> bool:
    """工序代码或工序序号含「摆剪」。"""
    return contains_swing_shear(process_code, process_seq)


def applied_swing_shear_fee_per_ton(*, has_swing_shear: bool, fee_per_ton: Decimal) -> Decimal:
    """本月核价实际加到钢价上的元/吨；非摆剪为 0（快照当时系统设置）。"""
    if not has_swing_shear:
        return Decimal("0")
    return fee_per_ton


def steel_kg_price_with_swing_shear(mill_ton_price: Decimal, fee_per_ton: Decimal) -> Decimal:
    """材料核算用钢板单价(元/kg) = (联动吨价 + 摆剪加价) / 1000。"""
    return (mill_ton_price + fee_per_ton) / KG_PER_TON
