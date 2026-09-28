"""采购对象列表筛选形状。"""

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


class ProcurementObjectScopeFilters(TypedDict):
    """列表 / HUD / 导出共用的对象行筛参。

    `bom_version` = 爬到的 L0 版本字浏览筛（可选），**不是**清单头键 / snapshot 键。
    """

    location: str | None
    locations: list[str] | None
    vehicle_model: str | None
    bom_version: str | None
    section: str | None
    object_kind: str | None
    confirm_status: str | None
    audit_status: str | None
    part_number: str | None
    l0_part_number: str | None
    excel_row: int | None
    supplier_names: list[str] | None
    has_supplier: bool | None
    # 仅「不含已过期」时由 Service 填墙钟本月；列表 API 禁止暴露 year/month
    as_of_year: int | None
    as_of_month: int | None


def object_scope_filters(
    *,
    location: str | None = None,
    locations: list[str] | None = None,
    vehicle_model: str | None = None,
    bom_version: str | None = None,
    section: str | None = None,
    object_kind: str | None = None,
    confirm_status: str | None = None,
    audit_status: str | None = None,
    part_number: str | None = None,
    l0_part_number: str | None = None,
    excel_row: int | None = None,
    supplier_names: list[str] | None = None,
    has_supplier: bool | None = None,
    as_of_year: int | None = None,
    as_of_month: int | None = None,
) -> ProcurementObjectScopeFilters:
    return {
        "location": location,
        "locations": locations,
        "vehicle_model": vehicle_model,
        "bom_version": bom_version,
        "section": section,
        "object_kind": object_kind,
        "confirm_status": confirm_status,
        "audit_status": audit_status,
        "part_number": part_number,
        "l0_part_number": l0_part_number,
        "excel_row": excel_row,
        "supplier_names": supplier_names,
        "has_supplier": has_supplier,
        "as_of_year": as_of_year,
        "as_of_month": as_of_month,
    }


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
