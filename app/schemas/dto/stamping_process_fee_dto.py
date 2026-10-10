"""
冲压加工费 DTO - 请求参数 / Repository 写入载荷
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q3, optional_quantize_money
from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
)


class StampingProcessFeeScopeDTO(BaseModel):
    """
    计算范围：年度 + 基地 + 项目必填。版本可选。
    工厂仅列表/批量删除收窄；计算与审核忽略。
    """

    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="年度")
    location: str = Field(..., min_length=1, description="基地")
    vehicle_model: str = Field(..., min_length=1, description="项目")
    version: str | None = Field(None, description="版本")
    stamping_supplier: str | None = Field(None, description="冲压工厂")

    @field_validator("vehicle_model", mode="before")
    @classmethod
    def _strip_vehicle(cls, value: object) -> str:
        return str(value).strip() if value is not None else ""

    @field_validator("version", "stamping_supplier", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class StampingProcessFeeCalcDTO(StampingProcessFeeScopeDTO):
    """加工费计算：按车型覆盖各厂；工厂字段忽略。"""


class StampingProcessFeeQuery(BaseModel):
    """冲压加工费列表查询参数"""

    year: int | None = Field(None, description="年度")
    location: str | None = Field(None, description="基地")
    stamping_supplier: str | None = Field(None, description="冲压工厂")
    vehicle_model: str | None = Field(None, description="项目")
    version: str | None = Field(None, description="版本")
    part_number: str | None = Field(None, description="零件号")
    audit_status: str | None = Field(None, description="审核状态")
    only_zero: bool = Field(
        False,
        description="仅看算费失败/零价待补价（确认单价为空或为 0）",
    )
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=500, description="每页条数")


class StampingProcessFeeUpdateDTO(BaseModel):
    """其它费用与备注"""

    other_fee: Decimal | None = Field(
        None,
        description="其它费用(元)，如拼焊费；可正可负；传 null 表示无其它费用",
    )
    remark: str | None = Field(None, max_length=1000, description="备注（调整理由/原因）")

    @field_validator("other_fee", mode="before")
    @classmethod
    def _coerce_other_fee(cls, value: object) -> Decimal | None:
        return optional_quantize_money(value, Q3)


class StampingProcessFeeDeleteDTO(StampingProcessFeeScopeDTO):
    """批量删除（仅删未审核；已通过跳过）"""


class StampingProcessFeeBatchApproveDTO(StampingProcessFeeScopeDTO):
    """批量审核通过"""

    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class StampingProcessFeeBatchReverseAuditDTO(StampingProcessFeeScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")


@dataclass(slots=True)
class ProcessFeePartSnapshot:
    """零件主表快照到加工费结果行。"""

    source_part_id: int | None
    seq_no: int | None
    part_number: str
    part_name: str | None
    material: str | None
    thickness: Decimal | None
    part_weight: Decimal | None
    sheet_length: Decimal | None
    sheet_width: Decimal | None
    parts_per_sheet: int | None
    sheet_type: str | None
    die_type: str | None
    process_method: str | None
    automation: str | None
    part_remark: str | None
    sketch_url: str | None
    excel_filename: str | None
    is_tailor_welded: bool = False


@dataclass(slots=True)
class ProcessFeeItemPayload:
    """加工费工序分项写入。"""

    source_process_id: int | None = None
    process_seq: str | None = None
    process_order: int | None = None
    process_code: str | None = None
    original_tonnage: int | None = None
    resolved_tonnage: int | None = None
    tonnage_source: str = "self"
    inherited_from_part_id: int | None = None
    inherited_from_part_number: str | None = None
    inherited_from_process_seq: str | None = None
    inherited_from_process_code: str | None = None
    cost_ratio: Decimal | None = None
    tonnage_price_id: int | None = None
    price_per_stroke: Decimal | None = None
    line_fee: Decimal = Decimal("0")
    basis_text: str | None = None
    remark: str | None = None


@dataclass(slots=True)
class ProcessFeeUpsertPayload:
    """加工费主表 upsert（含快照与工序分项）。"""

    year: int
    location: str
    stamping_supplier: str
    vehicle_model: str
    version: str
    snapshot: ProcessFeePartSnapshot
    processing_fee: Decimal | None
    process_count: int
    final_processing_fee: Decimal | None
    calc_fail_reason: str | None
    audit_status: str
    updated_by: str | None
    created_by: str | None = None
    process_items: list[ProcessFeeItemPayload] = field(default_factory=list)


class ProcessFeePatch(TypedDict, total=False):
    """加工费部分更新（其它费用等）。"""

    other_fee: Decimal | None
    final_processing_fee: Decimal | None
    remark: str | None
    updated_by: str


@dataclass(slots=True)
class ProcessFeeCalcLogCreate:
    """加工费计算日志新建。"""

    calc_batch_id: str
    year: int
    location: str
    stamping_supplier: str
    status: str
    detail_text: str
    started_at: datetime
    vehicle_model: str | None = None
    version: str | None = None
    operator_id: int | None = None
    operator_name: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


class ProcessFeeCalcLogPatch(TypedDict, total=False):
    """加工费计算日志部分更新。"""

    status: str
    total_parts: int
    success_count: int
    failed_count: int
    zero_fee_count: int
    skipped_approved_count: int
    detail_text: str
    finished_at: datetime
    updated_by: str | None
