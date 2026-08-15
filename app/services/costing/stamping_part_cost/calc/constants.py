"""冲压零件核价计算常量。"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

FORMULA_VERSION = "part-cost-v5"
AMOUNT_QUANTIZE = Decimal("0.000001")
UTIL_QUANTIZE = Decimal("0.01")
FEE_QUANTIZE = Decimal("0.001")

STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STALE_PROCESSING_SECONDS = 2 * 60 * 60

DUPLICATE_SCOPE_CALC_MESSAGE = "当前年度/月份/基地/工厂正在计算中，请勿重复提交。"
SCOPE_REQUIRED_MESSAGE = "须选定年度、月份、基地、冲压工厂。"


def quantize(value: Decimal, quant: Decimal) -> Decimal:
    return value.quantize(quant, rounding=ROUND_HALF_UP)
