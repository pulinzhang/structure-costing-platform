"""焊接费列表筛选形状。"""

from __future__ import annotations

from decimal import Decimal
from typing import TypedDict


class WeldingFeeFilterSummary(TypedDict):
    """列表筛选汇总（全量，无分页）。"""

    total_count: int
    total_fee: Decimal
    pending_count: int
    approved_count: int
    partial_count: int
    failed_count: int
    missing_price_count: int
