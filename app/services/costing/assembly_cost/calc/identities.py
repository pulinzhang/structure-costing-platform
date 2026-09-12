"""总成月核价 rollup：金额恒等式。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.common.money import Q4


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Q4, rounding=ROUND_HALF_UP)


def identities_hold(
    *,
    stamping_amount: Decimal,
    purchased_amount: Decimal,
    bundle_amount: Decimal,
    material_amount: Decimal,
    welding_amount: Decimal,
    welding_other_fee: Decimal,
    total_amount: Decimal,
    should_cost: Decimal,
    gauge_alloc_fee: Decimal,
    fixture_alloc_fee: Decimal,
    allocation_fee_total: Decimal,
    indirect_amount: Decimal,
    grand_total: Decimal,
    indirect_sum: Decimal,
) -> bool:
    checks = (
        material_amount == quantize_money(stamping_amount + purchased_amount + bundle_amount),
        total_amount == quantize_money(material_amount + welding_amount + welding_other_fee),
        should_cost == total_amount,
        allocation_fee_total == quantize_money(gauge_alloc_fee + fixture_alloc_fee),
        indirect_amount == quantize_money(indirect_sum),
        grand_total == quantize_money(total_amount + indirect_amount),
    )
    return all(checks)
