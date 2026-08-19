"""
L0 核对导出 — 单元格取值（与 Excel 样式无关）
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.common.bom.welding_standard_process import (
    WeldingStandardProcessName,
    resolve_standard_process_unit,
)
from app.models.bom import BomWeldingProcessBreakdownLine


def qty_cell(value: Any) -> Decimal | str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def standard_name(token: str | None, name: str | None) -> str:
    if name:
        return name
    if token in ("面积", "电泳面积"):
        return WeldingStandardProcessName.E_COAT_LE_244H.value
    return ""


def standard_unit(token: str | None, name: str | None, unit: str | None) -> str:
    if unit:
        return unit
    return resolve_standard_process_unit(standard_name(token, name)) or ""


def billing_qty_unit(
    line: BomWeldingProcessBreakdownLine,
) -> tuple[Decimal | str, str]:
    """有次要过程量则以其计费，否则用过程量。"""
    if line.process_qty_secondary is not None:
        return (
            qty_cell(line.process_qty_secondary),
            line.process_qty_secondary_unit or "",
        )
    return qty_cell(line.process_qty), line.process_qty_unit or ""


def filter_summary(
    *,
    location: str | None,
    customer_name: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    part_number: str | None,
    process_line_count_eq: int | None,
) -> str:
    parts = [
        "L0",
        f"基地 {location or '全部'}",
        f"项目 {vehicle_model or '全部'}",
        f"版本 {bom_version or '全部'}",
    ]
    if customer_name:
        parts.insert(2, f"顾客 {customer_name}")
    if part_number:
        parts.append(f"零件号 {part_number}")
    if process_line_count_eq is not None:
        parts.append(f"工艺数={process_line_count_eq}")
    return " · ".join(parts)


def build_filename(
    *,
    location: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    stamp: str,
) -> str:
    parts = ["焊接工艺拆解_L0核对"]
    if location:
        parts.append(location)
    if vehicle_model:
        parts.append(vehicle_model)
    if bom_version:
        parts.append(bom_version)
    return "_".join(parts) + f"_{stamp}.xlsx"
