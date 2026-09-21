"""BOM 清单仓储类型。"""

from typing import TypedDict


class BomSnapshotListSummary(TypedDict):
    """BOM 清单列表 HUD 汇总。"""

    total_count: int
    active_count: int
    draft_count: int
    archived_count: int
    total_node_count: int


class BomSnapshotListFilters(TypedDict):
    """BOM 清单列表筛选体。"""

    locations: list[str]
    vehicle_models: list[str]
    bom_versions: list[str]
    statuses: list[str]
    summary: BomSnapshotListSummary


class BomL0ScopeRow(TypedDict):
    """含 L0 节点的 BOM 快照 scope（location 为快照上实际字符串）。"""

    location: str
    vehicle_model: str
    bom_version: str
