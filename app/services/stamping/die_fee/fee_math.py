"""年度模具费金额计算（全程 Decimal）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.common.money import Q4, format_money, quantize_money

PRICE_KIND_PROGRESSIVE = "progressive"
PRICE_KIND_STEEL_PLATE = "steel_plate"

ZERO = Decimal("0")


def is_progressive_mode(production_mode: str | None) -> bool:
    return "级进模" in (production_mode or "")


def resolve_price_kind(production_mode: str | None) -> str:
    if is_progressive_mode(production_mode):
        return PRICE_KIND_PROGRESSIVE
    return PRICE_KIND_STEEL_PLATE


def calc_line_die_fee(
    *,
    estimated_weight_t: Decimal | None,
    unit_price: Decimal,
    alloc_ratio: Decimal | None,
    allocation_qty: Decimal,
) -> Decimal | None:
    """各序模具费（元）。算不出或量化后 ≤ 0 则 None。"""
    if allocation_qty <= ZERO:
        return None
    if estimated_weight_t is None or estimated_weight_t <= ZERO:
        return None
    ratio = alloc_ratio if alloc_ratio is not None else Decimal("1.00")
    raw = estimated_weight_t * unit_price * ratio / allocation_qty
    line = quantize_money(raw, Q4, allow_negative=False)
    if line <= ZERO:
        return None
    return line


def sum_line_fees(lines: list[Decimal]) -> Decimal:
    total = ZERO
    for line in lines:
        total += line
    return quantize_money(total, Q4, allow_negative=False)


def resolve_final_die_fee(
    die_fee: Decimal,
    adjustment_amount: Decimal | None,
) -> Decimal:
    """最终 = 系统 + 调整（空当 0）。"""
    adj = adjustment_amount if adjustment_amount is not None else ZERO
    return quantize_money(die_fee + adj, Q4, allow_negative=True)


def build_line_basis_text(
    *,
    estimated_weight_t: Decimal,
    unit_price: Decimal,
    alloc_ratio: Decimal,
    allocation_qty: Decimal,
    line_die_fee: Decimal,
    inherited_from_part_number: str | None = None,
    inherited_from_process_seq: str | None = None,
) -> str:
    weight = format_money(estimated_weight_t, Q4, 4)
    price = format_money(unit_price, Q4, 4)
    ratio = format_money(alloc_ratio, Decimal("0.01"), 2)
    qty = format_money(allocation_qty, Q4, 4)
    fee = format_money(line_die_fee, Q4, 4)
    inherit_bit = ""
    from_part = (inherited_from_part_number or "").strip()
    from_seq = (inherited_from_process_seq or "").strip()
    if from_part:
        seq_bit = f" {from_seq}" if from_seq else ""
        inherit_bit = f"继承 {from_part}{seq_bit} 重量；"
    return f"{inherit_bit}{weight} T × {price} 万元/吨 × {ratio} / {qty} 万台 = {fee} 元"


@dataclass(slots=True, frozen=True)
class DieFeeLineResult:
    process_seq: str
    process_order: int
    process_code: str | None
    source_die_process_id: int | None
    estimated_weight_t: Decimal
    alloc_ratio: Decimal
    die_sets: int | None
    line_die_fee: Decimal
    basis_text: str
