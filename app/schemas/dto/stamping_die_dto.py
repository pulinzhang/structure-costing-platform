"""冲压模具 DTO。"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class StampingDiePartInsert:
    location: str
    vehicle_model: str
    stamping_supplier: str | None
    version: str | None
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
    excel_filename: str
    excel_sheet_name: str | None
    excel_row: int | None
    excel_part_col: int | None
    created_by: str
    updated_by: str


@dataclass
class StampingDieProcessInsert:
    die_part_id: int
    process_seq: str
    process_order: int
    process_code: str | None
    die_sets: int | None
    die_number: str | None
    die_length: Decimal | None
    die_width: Decimal | None
    die_height: Decimal | None
    hollow_factor: Decimal | None
    estimated_weight_t: Decimal | None
    tonnage: int | None
    alloc_ratio: Decimal
    created_by: str
    updated_by: str
