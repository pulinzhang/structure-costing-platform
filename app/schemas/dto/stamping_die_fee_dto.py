"""冲压年度模具费 DTO。"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, TypedDict

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, optional_quantize_money
from app.common.vehicle_model import normalize_vehicle_model


class StampingDieFeeScopeDTO(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    location: str = Field(..., min_length=1)
    vehicle_model: str = Field(..., min_length=1)

    @field_validator("location", "vehicle_model", mode="before")
    @classmethod
    def _strip_required(cls, value: object) -> str:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValueError("不能为空")
        return text

    @field_validator("vehicle_model")
    @classmethod
    def _normalize_vehicle(cls, value: str) -> str:
        normalized = normalize_vehicle_model(value)
        if not normalized:
            raise ValueError("项目不能为空")
        return normalized


class StampingDieFeeCalcDTO(StampingDieFeeScopeDTO):
    """提交计算。按项目覆盖各厂；版本可选。锁范围：年+基地+项目。"""

    version: str | None = None

    @field_validator("version", mode="before")
    @classmethod
    def _strip_identity(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class StampingDieFeeQuery(BaseModel):
    """列表查询：年 / 基地 / 项目均可空；空=不限（默认全量）。"""

    year: int | None = Field(None, description="年度")
    location: str | None = Field(None, description="基地")
    vehicle_model: str | None = Field(None, description="项目")
    stamping_supplier: str | None = None
    version: str | None = None
    part_number: str | None = None
    audit_status: str | None = None
    only_zero: bool = False
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=500)

    @field_validator(
        "location",
        "vehicle_model",
        "stamping_supplier",
        "version",
        "part_number",
        "audit_status",
        mode="before",
    )
    @classmethod
    def _strip_optional(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("vehicle_model")
    @classmethod
    def _normalize_vehicle(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_vehicle_model(value) or None


class StampingDieFeeUpdateDTO(BaseModel):
    adjustment_amount: Decimal | None = Field(None, description="调整金额，可正可负")
    remark: str | None = Field(None, max_length=1000)

    @field_validator("adjustment_amount", mode="before")
    @classmethod
    def _coerce_adjustment(cls, value: Any) -> Decimal | None:
        return optional_quantize_money(value, Q4, allow_negative=True)


class StampingDieFeeDeleteDTO(StampingDieFeeScopeDTO):
    """按范围删未审核。"""


class StampingDieFeeBatchApproveDTO(StampingDieFeeScopeDTO):
    audit_remark: str = Field(..., min_length=1)


class StampingDieFeeBatchReverseAuditDTO(StampingDieFeeScopeDTO):
    reverse_audit_remark: str = Field(..., min_length=1)


@dataclass(slots=True)
class DieFeeItemPayload:
    source_die_process_id: int | None
    process_seq: str
    process_order: int
    process_code: str | None
    estimated_weight_t: Decimal
    alloc_ratio: Decimal
    die_sets: int | None
    unit_price: Decimal
    allocation_qty: Decimal
    price_kind: str
    line_die_fee: Decimal
    basis_text: str | None


@dataclass(slots=True)
class DieFeeInsertPayload:
    year: int
    location: str
    vehicle_model: str
    stamping_supplier: str | None
    version: str | None
    part_number: str
    source_die_part_id: int | None
    seq_no: int | None
    part_name: str | None
    material: str | None
    thickness: Decimal | None
    part_weight: Decimal | None
    die_type: str | None
    die_method: str | None
    production_mode: str | None
    part_grade: str | None
    excel_filename: str | None
    price_kind: str
    unit_price: Decimal
    allocation_qty: Decimal
    die_fee: Decimal
    adjustment_amount: Decimal | None
    final_die_fee: Decimal
    audit_status: str
    created_by: str | None
    updated_by: str | None
    items: list[DieFeeItemPayload] = field(default_factory=list)


class DieFeePatch(TypedDict, total=False):
    adjustment_amount: Decimal | None
    final_die_fee: Decimal
    remark: str | None
    updated_by: str


@dataclass(slots=True)
class DieFeeCalcLogCreate:
    calc_batch_id: str
    year: int
    location: str
    vehicle_model: str
    status: str
    detail_text: str
    started_at: datetime
    stamping_supplier: str | None = None
    version: str | None = None
    operator_id: int | None = None
    operator_name: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


class DieFeeCalcLogPatch(TypedDict, total=False):
    status: str
    total_parts: int
    success_count: int
    skipped_no_die_count: int
    failed_count: int
    detail_text: str
    finished_at: datetime
    updated_by: str | None
