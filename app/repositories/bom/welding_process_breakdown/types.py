"""焊接工艺拆解列表筛选形状。"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class WeldingBreakdownFilterSummary(TypedDict):
    """列表筛选汇总。"""

    total_count: int
    pending_count: int
    approved_count: int
    l0_count: int
    l0_zero_process_count: NotRequired[int]


class WeldingBreakdownListFilters(TypedDict):
    """焊接工艺拆解列表筛选体。"""

    locations: list[str]
    customer_names: list[str]
    vehicle_models: list[str]
    bom_versions: list[str]
    standard_process_names: list[str]
    audit_status: str | None
    summary: WeldingBreakdownFilterSummary
