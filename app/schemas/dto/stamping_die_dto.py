"""冲压模具 DTO。"""

from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q2, quantize_money


class StampingDiePartQuery(BaseModel):
    location: str = ""
    vehicle_model: str = ""
    part_number: str | None = None
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)
    year: int | None = Field(None, ge=2000, le=2100, description="查看年；空则墙钟")
    month: int | None = Field(None, ge=1, le=12, description="查看月；与年同空或同有")
    include_expired: bool = Field(False, description="含已失效；模具清单不提供开关")

    @field_validator("part_number", mode="before")
    @classmethod
    def _strip_optional(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class StampingDieScopeDTO(BaseModel):
    location: str = Field(..., min_length=1)
    vehicle_model: str = Field(..., min_length=1)


class StampingDieAllocRatioUpdate(BaseModel):
    alloc_ratio: Decimal

    @field_validator("alloc_ratio", mode="before")
    @classmethod
    def _ratio(cls, value: object) -> Decimal:
        return quantize_money(value, Q2)


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
    effective_year: int
    effective_month: int
    expiry_year: int | None = None
    expiry_month: int | None = None


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
    remark: str | None = None
