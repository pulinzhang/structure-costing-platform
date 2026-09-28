"""采购对象列表导出 — 行值、检测摘要、文件名。"""

from __future__ import annotations

from datetime import datetime

from app.common.bom.manufacturing_category import short_part_number_digits
from app.common.period import format_period
from app.models.bom.procurement_object import BomProcurementObject
from app.schemas.dto.bom_procurement_object_dto import BomProcurementObjectQuery
from app.services.bom.procurement_object.labels import (
    AUDIT_LABELS,
    CONFIRM_LABELS,
    KIND_LABELS,
    SECTION_LABELS,
    SUBTYPE_LABELS,
)
from app.services.bom.procurement_object.mapping import L0Period

ExcelCell = str | int | None


def kind_label(row: BomProcurementObject) -> str:
    if row.object_kind:
        return KIND_LABELS.get(row.object_kind, row.object_kind)
    return SECTION_LABELS.get(row.section, "—")


def qa_summary(rows: list[BomProcurementObject]) -> tuple[str, bool]:
    headers = {id(row.object_list): row.object_list for row in rows if row.object_list}
    if not headers:
        return "尚未生成或当前筛选无行", True
    failed = [item for item in headers.values() if not item.qa_passed]
    if failed:
        return "检测未通过（仍可确认/审核，已审行跳过不改）", False
    return "检测通过", True


def scope_text(query: BomProcurementObjectQuery) -> str:
    location = (query.location or "").strip() or "全部基地"
    model = (query.vehicle_model or "").strip() or "全部项目"
    version = (query.bom_version or "").strip() or "全部版本"
    return f"{location} · {model} · {version}"


def build_filename(query: BomProcurementObjectQuery, stamp: datetime) -> str:
    parts = ["采购对象列表"]
    if query.location:
        parts.append(query.location.strip())
    if query.vehicle_model:
        parts.append(query.vehicle_model.strip())
    if query.bom_version:
        parts.append(query.bom_version.strip())
    return "_".join(parts) + f"_{stamp.strftime('%Y%m%d_%H%M%S')}.xlsx"


def row_values(
    row: BomProcurementObject,
    *,
    l0_period: L0Period | None = None,
) -> list[ExcelCell]:
    header = row.object_list
    return [
        row.excel_row,
        row.excel_sheet_name or "",
        row.part_number,
        short_part_number_digits(row.part_number),
        row.internal_number or None,
        row.part_name or "",
        row.l0_part_number,
        row.l0_part_name or "",
        kind_label(row),
        CONFIRM_LABELS.get(row.confirm_status, row.confirm_status),
        row.supplier_name or "",
        AUDIT_LABELS.get(row.audit_status, row.audit_status),
        row.material or "",
        row.thickness_text or "",
        row.material_mill or "",
        row.weld_info or "",
        row.remark or "",
        SUBTYPE_LABELS.get(row.degenerate_subtype or "", row.degenerate_subtype or ""),
        row.level,
        row.excel_filename or (header.source_filename if header else ""),
        header.location if header else "",
        header.vehicle_model if header else "",
        header.bom_version if header else "",
        period_label(l0_period),
    ]


def period_label(l0_period: L0Period | None) -> str:
    if l0_period is None:
        return "—"
    effective_year, effective_month, expiry_year, expiry_month = l0_period
    start = format_period(effective_year, effective_month)
    end = (
        format_period(expiry_year, expiry_month)
        if expiry_year is not None and expiry_month is not None
        else "未结束"
    )
    return f"{start} – {end}"


def l0_merge_key(row: BomProcurementObject) -> tuple[str, ...]:
    return (row.l0_part_number or "", row.l0_part_name or "")


def excel_filename_key(row: BomProcurementObject) -> tuple[str, ...]:
    header = row.object_list
    name = row.excel_filename or (header.source_filename if header else "") or ""
    return (name,)


def excel_sheet_key(row: BomProcurementObject) -> tuple[str, ...]:
    sheet_name = row.excel_sheet_name or ""
    return (*excel_filename_key(row), sheet_name)
