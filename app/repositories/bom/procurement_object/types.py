"""采购对象清单筛选形状。"""

from typing import TypedDict

from sqlalchemy import case, func
from sqlalchemy.sql.elements import ColumnElement

# 与 classify 同值；本层不 import Service，避免仓储→服务成环
SECTION_OBJECT = "object"
KIND_L0_DEGENERATE = "l0_degenerate"


class ProcurementObjectAuditSummary(TypedDict):
    total_count: int
    pending_count: int
    approved_count: int
    object_count: int
    object_l0_degenerate_count: int
    other_leaf_count: int
    anomaly_count: int


def count_matching(*conditions: ColumnElement[bool]) -> ColumnElement[int]:
    """HUD 分桶：所列条件同时成立计 1。新增看板计数只加一列 label，不要再 .count()。"""
    predicate = conditions[0]
    for extra in conditions[1:]:
        predicate = predicate & extra
    return func.coalesce(func.sum(case((predicate, 1), else_=0)), 0)


def empty_procurement_object_summary() -> ProcurementObjectAuditSummary:
    return {
        "total_count": 0,
        "pending_count": 0,
        "approved_count": 0,
        "object_count": 0,
        "object_l0_degenerate_count": 0,
        "other_leaf_count": 0,
        "anomaly_count": 0,
    }
