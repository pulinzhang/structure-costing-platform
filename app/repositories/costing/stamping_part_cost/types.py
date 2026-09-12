"""冲压零件核价列表筛选形状。"""

from decimal import Decimal
from typing import TypedDict


class PartCostFilterSummary(TypedDict):
    """列表 HUD 汇总（全量筛选，非本页）。字段名 = 列名 + _sum，避免和行上金额撞名。"""

    unit_cost_sum: Decimal
    avg_unit_cost: Decimal | None
    material_net_per_part_sum: Decimal
    process_fee_amount_sum: Decimal
    pending_count: int
    approved_count: int


def empty_part_cost_summary() -> PartCostFilterSummary:
    return {
        "unit_cost_sum": Decimal("0"),
        "avg_unit_cost": None,
        "material_net_per_part_sum": Decimal("0"),
        "process_fee_amount_sum": Decimal("0"),
        "pending_count": 0,
        "approved_count": 0,
    }


class PartCostListFilters(TypedDict):
    """零件核价列表筛选体。"""

    years: list[int]
    months: list[int]
    locations: list[str]
    suppliers: list[str]
    vehicle_models: list[str]
    versions: list[str]
    summary: PartCostFilterSummary
