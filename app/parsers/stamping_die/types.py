"""冲压模具布点解析结果类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TypedDict


class DieColumnMap(TypedDict, total=False):
    seq_no: int
    part_number: int
    part_name: int
    material: int
    thickness: int
    part_weight: int
    sheet_length: int
    sheet_width: int
    sheet_shape: int
    parts_per_sheet: int
    material_consumption: int
    material_utilization: int
    process_seq: int
    process_code: int
    die_sets: int
    die_number: int
    die_length: int
    die_width: int
    die_height: int
    hollow_factor: int
    estimated_weight_t: int
    estimated_weight_subtotal_t: int
    tonnage: int
    die_type: int
    die_method: int
    production_mode: int
    needs_end_effector: int
    part_grade: int
    remark: int


@dataclass(slots=True)
class ParsedDieProcess:
    process_seq: str
    process_code: str | None
    die_sets: int | None
    die_number: str | None
    die_length: Decimal | None
    die_width: Decimal | None
    die_height: Decimal | None
    hollow_factor: Decimal | None
    estimated_weight_t: Decimal | None
    tonnage: int | None
    excel_row: int | None = None


@dataclass(slots=True)
class ParsedDiePart:
    seq_no: int | None
    part_number: str
    part_name: str | None
    material: str | None
    thickness: Decimal | None
    part_weight: Decimal | None
    sheet_length: Decimal | None
    sheet_width: Decimal | None
    sheet_shape: str | None
    parts_per_sheet: int | None
    material_consumption: Decimal | None
    material_utilization: Decimal | None
    estimated_weight_subtotal_t: Decimal | None
    die_type: str | None
    die_method: str | None
    production_mode: str | None
    needs_end_effector: str | None
    part_grade: str | None
    remark: str | None
    excel_sheet_name: str | None
    excel_row: int | None
    excel_part_col: int
    is_scrap_byproduct: bool = False
    processes: list[ParsedDieProcess] = field(default_factory=list)


@dataclass(slots=True)
class DieParseResult:
    vehicle_model: str | None
    sheet_name: str
    parts: list[ParsedDiePart]
