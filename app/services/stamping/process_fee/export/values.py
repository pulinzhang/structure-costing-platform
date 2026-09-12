"""冲压加工费导出 — 单元格取值、筛选摘要、文件名。"""

from __future__ import annotations

from decimal import Decimal

from app.common.audit import audit_status_label
from app.common.bom.manufacturing_category import short_part_number_digits
from app.common.money import Q3, Q4, excel_money_cell
from app.common.timezone import now
from app.models.stamping.process_fee import StampingProcessFee
from app.models.stamping.process_fee_item import StampingProcessFeeItem
from app.services.stamping.process_fee.export.columns import DATA_H

_TONNAGE_SOURCE_LABEL = {
    "self": "自有",
    "inherited": "继承",
    "swing_shear": "摆剪",
}


def money_cell(value: object, quant: Decimal = Q3) -> Decimal | str:
    return excel_money_cell(value, quant)


def filter_text(
    *,
    year: int | None,
    location: str | None,
    stamping_supplier: str | None,
    vehicle_model: str | None,
    version: str | None,
    part_number: str | None,
    audit_status: str | None,
) -> str:
    parts: list[str] = []
    if year is not None:
        parts.append(f"年度={year}")
    if location:
        parts.append(f"基地={location}")
    if stamping_supplier:
        parts.append(f"冲压工厂={stamping_supplier}")
    if vehicle_model:
        parts.append(f"项目={vehicle_model}")
    if version:
        parts.append(f"版本={version}")
    if part_number:
        parts.append(f"零件号含={part_number}")
    if audit_status:
        parts.append(f"审核={audit_status_label(audit_status)}")
    return " · ".join(parts) if parts else "全部筛选"


def build_filename(
    *,
    year: int | None,
    location: str | None,
    stamping_supplier: str | None,
    vehicle_model: str | None,
) -> str:
    stamp = now().strftime("%Y%m%d_%H%M%S")
    parts = ["冲压加工费"]
    if year:
        parts.append(f"{year}年")
    if location:
        parts.append(location)
    if vehicle_model:
        parts.append(vehicle_model)
    if stamping_supplier:
        parts.append(stamping_supplier)
    return "_".join(parts) + f"_{stamp}.xlsx"


def row_height(item: StampingProcessFeeItem) -> float:
    basis = (item.basis_text or "").strip()
    extra = 0.0
    if len(basis) > 40:
        extra = min(36.0, (len(basis) // 40) * 8.0)
    return DATA_H + extra


def main_values(record: StampingProcessFee, *, seq_no: int) -> list[object]:
    return [
        seq_no,
        record.year,
        record.location,
        record.stamping_supplier,
        record.vehicle_model,
        record.version,
        record.part_number,
        short_part_number_digits(record.part_number) or "",
        record.part_name or "",
        record.material or "",
        money_cell(record.thickness, Q4),
        record.process_count,
        money_cell(record.processing_fee, Q3),
        money_cell(record.other_fee, Q3),
        money_cell(record.final_processing_fee, Q3),
    ]


def detail_values(item: StampingProcessFeeItem | None) -> list[object]:
    tonnage_source = (item.tonnage_source if item else "") or ""
    return [
        (item.process_seq or "") if item else "",
        (item.process_code or "") if item else "",
        item.resolved_tonnage if item and item.resolved_tonnage is not None else "",
        _TONNAGE_SOURCE_LABEL.get(tonnage_source, tonnage_source) if item else "",
        money_cell(item.cost_ratio, Q4) if item and item.cost_ratio is not None else "",
        money_cell(item.price_per_stroke, Q3) if item and item.price_per_stroke is not None else "",
        money_cell(item.line_fee, Q3) if item else "",
        (item.basis_text or "").strip() if item else "",
    ]
