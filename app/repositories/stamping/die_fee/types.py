"""冲压模具费列表筛选形状。"""

from decimal import Decimal
from typing import TypedDict


class DieFeeFilterSummary(TypedDict):
    total_count: int
    pending_count: int
    approved_count: int
    zero_count: int
    total_fee: Decimal
    avg_fee: Decimal


def sql_money(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))
