"""冲压零件核价计算常量。"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.common.money import Q3

FORMULA_VERSION = "part-cost-v9"
AMOUNT_QUANTIZE = Decimal("0.000001")
UTIL_QUANTIZE = Decimal("0.01")
FEE_QUANTIZE = Q3

STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STALE_PROCESSING_SECONDS = 2 * 60 * 60

DUPLICATE_SCOPE_CALC_MESSAGE = "当前年度/月份/基地/工厂正在计算中，请勿重复提交。"
SCOPE_REQUIRED_MESSAGE = "须选定年度、月份、基地、冲压工厂。"


def quantize(value: Decimal, quant: Decimal) -> Decimal:
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def compute_finished_cost_stack(
    *,
    material_net_per_part: Decimal,
    process_fee_amount: Decimal,
    finance_rate: Decimal,
    management_rate: Decimal,
    warehouse_packaging_rate: Decimal,
    pretax_profit_rate: Decimal,
    die_fee_amount: Decimal = Decimal("0"),
    gauge_fee_amount: Decimal = Decimal("0"),
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    """直接成本与四项成品费用 → 单件成本。

    直接成本 = 原材料净成本 R + 加工费 + 模具费 + 检具费。
    无模具/检具档案时金额为 0。

    Returns:
        (direct_cost, finance_fee, management_fee,
         warehouse_packaging_fee, pretax_profit_fee, unit_cost)
    """
    direct_cost = quantize(
        material_net_per_part + process_fee_amount + die_fee_amount + gauge_fee_amount,
        AMOUNT_QUANTIZE,
    )
    finance_fee = quantize(direct_cost * finance_rate, AMOUNT_QUANTIZE)
    management_fee = quantize(direct_cost * management_rate, AMOUNT_QUANTIZE)
    warehouse_packaging_fee = quantize(direct_cost * warehouse_packaging_rate, AMOUNT_QUANTIZE)
    pretax_profit_fee = quantize(direct_cost * pretax_profit_rate, AMOUNT_QUANTIZE)
    unit_cost = quantize(
        direct_cost + finance_fee + management_fee + warehouse_packaging_fee + pretax_profit_fee,
        AMOUNT_QUANTIZE,
    )
    return (
        direct_cost,
        finance_fee,
        management_fee,
        warehouse_packaging_fee,
        pretax_profit_fee,
        unit_cost,
    )
