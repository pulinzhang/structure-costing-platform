"""冲压模具 VO / 请求 DTO。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.common.money import Q2, Q4, format_money, optional_format_money, quantize_money
from app.common.timezone import datetime_to_iso


class StampingDiePartQuery(BaseModel):
    location: str = ""
    vehicle_model: str = ""
    part_number: str | None = None
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)


class StampingDieScopeDTO(BaseModel):
    location: str = Field(..., min_length=1)
    vehicle_model: str = Field(..., min_length=1)


class StampingDieAllocRatioUpdate(BaseModel):
    alloc_ratio: Decimal

    @field_validator("alloc_ratio", mode="before")
    @classmethod
    def _ratio(cls, value: object) -> Decimal:
        return quantize_money(value, Q2)


class StampingDieProcessVO(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    die_part_id: int
    process_seq: str
    process_order: int
    process_code: str | None = None
    die_sets: int | None = None
    die_number: str | None = None
    die_length: Decimal | None = None
    die_width: Decimal | None = None
    die_height: Decimal | None = None
    hollow_factor: Decimal | None = None
    estimated_weight_t: Decimal | None = None
    tonnage: int | None = None
    alloc_ratio: Decimal

    @field_serializer("die_length", "die_width", "die_height")
    def serialize_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)

    @field_serializer("hollow_factor", "estimated_weight_t")
    def serialize_q4(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("alloc_ratio")
    def serialize_ratio(self, value: Decimal) -> str:
        return format_money(value, Q2, 2)


class StampingDiePartListVO(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    location: str
    vehicle_model: str
    seq_no: int | None = None
    part_number: str
    part_name: str | None = None
    die_type: str | None = None
    die_method: str | None = None
    production_mode: str | None = None
    estimated_weight_subtotal_t: Decimal | None = None
    process_count: int = 0

    @field_serializer("estimated_weight_subtotal_t")
    def serialize_weight(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)


class StampingDiePartDetailVO(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    location: str
    vehicle_model: str
    seq_no: int | None = None
    part_number: str
    part_name: str | None = None
    material: str | None = None
    thickness: Decimal | None = None
    part_weight: Decimal | None = None
    sheet_length: Decimal | None = None
    sheet_width: Decimal | None = None
    sheet_shape: str | None = None
    parts_per_sheet: int | None = None
    material_consumption: Decimal | None = None
    material_utilization: Decimal | None = None
    estimated_weight_subtotal_t: Decimal | None = None
    die_type: str | None = None
    die_method: str | None = None
    production_mode: str | None = None
    needs_end_effector: str | None = None
    part_grade: str | None = None
    remark: str | None = None
    excel_filename: str | None = None
    excel_sheet_name: str | None = None
    excel_row: int | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    processes: list[StampingDieProcessVO] = []

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    @field_serializer(
        "thickness",
        "part_weight",
        "material_consumption",
        "material_utilization",
        "estimated_weight_subtotal_t",
    )
    def serialize_q4(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("sheet_length", "sheet_width")
    def serialize_q2(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)


class StampingDieScopeFilterVO(BaseModel):
    locations: list[str]
    vehicle_models: list[str]


class StampingDieBatchDeleteResultVO(BaseModel):
    deleted_parts: int
