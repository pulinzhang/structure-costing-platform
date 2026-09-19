"""采购对象清单 — ORM 行转 VO；列表/导出共用树根期。"""

from __future__ import annotations

from typing import Any, TypedDict, cast

from sqlalchemy.orm import Session

from app.common.period import resolve_as_of_month
from app.models.bom.procurement_object import BomProcurementObject
from app.repositories.bom.procurement_object.queries import L0Period
from app.repositories.bom.procurement_object_repository import (
    BomProcurementObjectRepository,
    ProcurementObjectScopeFilters,
    object_scope_filters,
)
from app.schemas.dto.bom_procurement_object_dto import BomProcurementObjectQuery
from app.schemas.vo.bom_procurement_object_vo import BomProcurementObjectVO

__all__ = [
    "L0Period",
    "as_of_when_excluding_expired",
    "l0_period_for_row",
    "load_l0_period_map",
    "row_to_vo",
    "rows_to_vos",
    "scope_from_query",
]


class _ObjectVoOverlay(TypedDict, total=False):
    """清单头字段 + 所属树根四列；禁止当成 ORM 列。"""

    location: str
    vehicle_model: str
    bom_version: str
    source_filename: str
    qa_passed: bool
    effective_year: int
    effective_month: int
    expiry_year: int | None
    expiry_month: int | None


def as_of_when_excluding_expired(include_expired: bool) -> tuple[int | None, int | None]:
    """不含已过期 → 墙钟本月；包含已过期 → 不过滤。"""
    if include_expired:
        return None, None
    return resolve_as_of_month(None, None)


def scope_from_query(
    query: BomProcurementObjectQuery,
    *,
    locations: list[str] | None = None,
    location: str | None = None,
    supplier_names: list[str] | None = None,
    as_of_year: int | None = None,
    as_of_month: int | None = None,
) -> ProcurementObjectScopeFilters:
    """列表用 locations（expand）；导出用 location（精确）。"""
    return object_scope_filters(
        location=location,
        locations=locations,
        vehicle_model=query.vehicle_model,
        bom_version=query.bom_version,
        section=query.section,
        object_kind=query.object_kind,
        confirm_status=query.confirm_status,
        audit_status=query.audit_status,
        part_number=query.part_number,
        l0_part_number=query.l0_part_number,
        excel_row=query.excel_row,
        supplier_names=supplier_names,
        has_supplier=query.has_supplier,
        as_of_year=as_of_year,
        as_of_month=as_of_month,
    )


def _snapshot_l0_key(row: BomProcurementObject) -> tuple[int, str] | None:
    if row.object_list is None or not row.l0_part_number:
        return None
    return (row.object_list.snapshot_id, row.l0_part_number)


def load_l0_period_map(
    db: Session,
    repository: BomProcurementObjectRepository,
    rows: list[BomProcurementObject],
) -> dict[tuple[int, str], L0Period]:
    keys = [key for row in rows if (key := _snapshot_l0_key(row)) is not None]
    return repository.map_l0_periods(db, snapshot_l0_keys=keys)


def l0_period_for_row(
    row: BomProcurementObject,
    period_map: dict[tuple[int, str], L0Period],
) -> L0Period | None:
    key = _snapshot_l0_key(row)
    if key is None:
        return None
    return period_map.get(key)


def _to_object_vo(
    row: BomProcurementObject,
    *,
    l0_period: L0Period | None = None,
) -> BomProcurementObjectVO:
    header = row.object_list
    vo = BomProcurementObjectVO.model_validate(row)
    update: _ObjectVoOverlay = {
        "location": header.location,
        "vehicle_model": header.vehicle_model,
        # 清单头冗余 SOP 字（展示副本）；列表浏览筛真相是爬到的 L0，勿当 WHERE
        "bom_version": header.bom_version,
        "source_filename": header.source_filename,
        "qa_passed": header.qa_passed,
    }
    if l0_period is not None:
        effective_year, effective_month, expiry_year, expiry_month = l0_period
        update["effective_year"] = effective_year
        update["effective_month"] = effective_month
        update["expiry_year"] = expiry_year
        update["expiry_month"] = expiry_month
    return vo.model_copy(update=cast(dict[str, Any], update))


def rows_to_vos(
    db: Session,
    repository: BomProcurementObjectRepository,
    rows: list[BomProcurementObject],
) -> list[BomProcurementObjectVO]:
    period_map = load_l0_period_map(db, repository, rows)
    return [_to_object_vo(row, l0_period=l0_period_for_row(row, period_map)) for row in rows]


def row_to_vo(
    db: Session,
    repository: BomProcurementObjectRepository,
    row: BomProcurementObject,
) -> BomProcurementObjectVO:
    return rows_to_vos(db, repository, [row])[0]
