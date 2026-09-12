"""钢材价格列表筛选形状。"""

from decimal import Decimal
from typing import TypedDict


class SteelPriceFilterSummary(TypedDict):
    """列表筛选汇总：均价 / 待审 / 已审。"""

    avg_final_price: Decimal | None
    pending_count: int
    approved_count: int


class SteelPriceFilterOptionValues(TypedDict):
    """筛选下拉选项（不含列表汇总，汇总由 Service 拼入）。"""

    years: list[int]
    months: list[int]
    locations: list[str]
    category_names: list[str]
    steel_mills: list[str]
    audit_statuses: list[str]
