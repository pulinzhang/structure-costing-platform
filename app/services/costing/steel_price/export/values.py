"""钢材联动价导出 — 单元格取值、筛选摘要、文件名。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.common.audit import audit_status_label
from app.common.money import Q4, excel_money_cell
from app.common.timezone import now
from app.models.costing.steel_price import SteelPrice
from app.services.costing.steel_price.spec_format import (
    build_spec,
    format_thickness,
    format_width,
)


def money_cell(value: object, quant: Decimal = Q4, *, allow_negative: bool = True) -> Decimal | str:
    return excel_money_cell(value, quant, allow_negative=allow_negative)


def money_cell_blank_zero(
    value: object,
    quant: Decimal = Q4,
    *,
    allow_negative: bool = True,
) -> Decimal | str:
    """单价为 0 / 空时导出空白，避免表里一堆 0。"""
    if value is None:
        return ""
    cell = excel_money_cell(value, quant, allow_negative=allow_negative)
    if isinstance(cell, Decimal) and cell == 0:
        return ""
    if cell == "" or cell == 0:
        return ""
    return cell


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    return f"{value:%Y-%m-%d %H:%M:%S}"


def filter_text(
    *,
    year: int | None,
    month: int | None,
    location: str | None,
    category_name: str | None,
    grade: str | None,
    steel_mill: str | None,
    audit_status: str | None,
) -> str:
    parts: list[str] = []
    if year:
        parts.append(f"{year}年")
    if month:
        parts.append(f"{month}月")
    if location:
        parts.append(location)
    if category_name:
        parts.append(category_name)
    if steel_mill:
        parts.append(steel_mill)
    if grade:
        parts.append(grade)
    if audit_status:
        parts.append(audit_status_label(audit_status))
    return " · ".join(parts) if parts else "全部筛选"


def build_filename(
    *,
    year: int | None,
    month: int | None,
    location: str | None,
    category_name: str | None,
    grade: str | None,
    steel_mill: str | None,
    audit_status: str | None,
) -> str:
    scope_parts = [
        f"{year}年" if year else None,
        f"{month}月" if month else None,
        location,
        category_name,
        steel_mill,
        grade,
        audit_status_label(audit_status) if audit_status else None,
    ]
    scope = "_".join(part for part in scope_parts if part) or "筛选"
    stamp = now().strftime("%Y%m%d_%H%M%S")
    return f"钢材联动价格_{scope}_{stamp}.xlsx"


def row_values(record: SteelPrice) -> list[object]:
    return [
        record.id,
        record.year,
        record.month,
        record.location or "",
        record.steel_mill or "",
        record.category_name or "",
        record.grade or "",
        format_thickness(record.thickness),
        format_width(record.width),
        build_spec(record.thickness, record.width),
        money_cell_blank_zero(record.base_price, Q4),
        money_cell_blank_zero(record.thickness_adjustment, Q4, allow_negative=True),
        money_cell_blank_zero(record.width_adjustment, Q4, allow_negative=True),
        money_cell_blank_zero(record.zinc_adjustment, Q4, allow_negative=True),
        money_cell_blank_zero(record.processing_fee, Q4),
        money_cell_blank_zero(record.other_adjustment, Q4, allow_negative=True),
        money_cell(record.final_price_per_ton, Q4),
        record.base_price_id or "",
        record.base_excel_filename or "",
        record.base_sheet_name or "",
        record.base_excel_row if record.base_excel_row is not None else "",
        record.base_excel_col if record.base_excel_col is not None else "",
        record.thickness_policy_id or "",
        record.thickness_ladder_item_id or "",
        record.thickness_excel_filename or "",
        record.thickness_sheet_name or "",
        record.thickness_excel_row if record.thickness_excel_row is not None else "",
        record.thickness_excel_col if record.thickness_excel_col is not None else "",
        record.width_policy_id or "",
        record.width_ladder_item_id or "",
        record.width_excel_filename or "",
        record.width_sheet_name or "",
        record.width_excel_row if record.width_excel_row is not None else "",
        record.width_excel_col if record.width_excel_col is not None else "",
        record.zinc_policy_id or "",
        record.zinc_ladder_item_id or "",
        record.zinc_excel_filename or "",
        record.zinc_sheet_name or "",
        record.zinc_excel_row if record.zinc_excel_row is not None else "",
        record.zinc_excel_col if record.zinc_excel_col is not None else "",
        record.match_status or "",
        record.calc_status or "",
        record.calc_message or "",
        record.calc_batch_id or "",
        record.formula_version or "",
        format_datetime(record.calculated_at),
        audit_status_label(record.audit_status),
        record.audited_by or "",
        format_datetime(record.audited_at),
        record.audit_remark or "",
        record.reverse_audited_by or "",
        format_datetime(record.reverse_audited_at),
        record.reverse_audit_remark or "",
        record.remark or "",
        record.created_by or "",
        format_datetime(record.created_at),
        record.updated_by or "",
        format_datetime(record.updated_at),
    ]
