"""冲压零件价格核算 DTO / Repository 写入载荷。"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, TypedDict

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q6, quantize_money


class StampingPartCostScopeDTO(BaseModel):
    """范围：年度 + 月份 + 基地 + 冲压工厂。"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    location: str = Field(..., min_length=1, description="基地")
    stamping_supplier: str = Field(..., min_length=1, description="冲压工厂")


class StampingPartCostCalcDTO(StampingPartCostScopeDTO):
    """计算请求（车型/版本可选）。"""

    vehicle_model: str | None = Field(None, description="车型")
    version: str | None = Field(None, description="版本")


class StampingPartCostQuery(BaseModel):
    """列表查询参数。"""

    year: int | None = Field(None, description="年度")
    month: int | None = Field(None, description="月份")
    location: str | None = Field(None, description="基地")
    stamping_supplier: str | None = Field(None, description="冲压工厂")
    vehicle_model: str | None = Field(None, description="车型")
    version: str | None = Field(None, description="版本")
    part_number: str | None = Field(None, description="零件号")
    audit_status: str | None = Field(None, description="审核状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=500, description="每页条数")


class StampingPartCostDeleteDTO(StampingPartCostScopeDTO):
    """批量删除（仅删未审核）。"""


class StampingPartCostBatchApproveDTO(StampingPartCostScopeDTO):
    """批量审核通过。"""

    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class StampingPartCostBatchReverseAuditDTO(StampingPartCostScopeDTO):
    """批量反审核。"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因")


class StampingPartCostManualUnitCostDTO(BaseModel):
    """失败记录手工录入最终单件成本。"""

    unit_cost: Decimal = Field(..., ge=0, description="最终单件成本（元）")
    remark: str = Field(..., min_length=1, description="改价备注（必填）")

    @field_validator("unit_cost", mode="before")
    @classmethod
    def _coerce_unit_cost(cls, value: Any) -> Decimal:
        return quantize_money(value, Q6)


@dataclass(slots=True)
class StampingPartCostPartSnapshot:
    """零件主表快照到核价结果行（含本月是否利废 / 利用哪类废料）。"""

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
    is_offal_nested: bool
    offal_source: str | None
    die_type: str | None
    process_method: str | None
    automation: str | None
    part_remark: str | None
    sketch_url: str | None
    excel_filename: str | None
    excel_sheet_name: str | None
    excel_row: int | None
    excel_part_col: int | None


@dataclass(slots=True)
class StampingPartCostCalcAmounts:
    """单件核价过程量与金额（计算器产出）。"""

    density: Decimal
    material_loss_rate: Decimal
    scrap_recovery_rate: Decimal
    blank_weight_kg: Decimal | None
    finished_total_kg: Decimal | None
    scrap_weight_kg: Decimal | None
    material_utilization_pct: Decimal | None
    steel_price_id: int | None
    steel_mill: str | None
    steel_ton_price: Decimal | None
    scrap_price_id: int | None
    scrap_ton_price: Decimal | None
    process_fee_id: int | None
    process_fee_amount: Decimal | None
    die_fee_id: int | None
    die_fee_amount: Decimal | None
    gauge_fee_id: int | None
    gauge_fee_amount: Decimal | None
    material_amount_sheet: Decimal | None
    loss_scrap_deduction: Decimal | None
    process_scrap_deduction: Decimal | None
    scrap_amount_sheet: Decimal | None
    material_net_per_part: Decimal | None
    direct_cost: Decimal | None
    finished_finance_fee: Decimal | None
    finished_management_fee: Decimal | None
    finished_warehouse_packaging_fee: Decimal | None
    finished_pretax_profit_fee: Decimal | None
    unit_cost: Decimal | None


@dataclass(slots=True)
class StampingPartCostUpsertPayload:
    """零件核价结果 upsert。"""

    year: int
    month: int
    location: str
    stamping_supplier: str
    vehicle_model: str
    version: str
    snapshot: StampingPartCostPartSnapshot
    density: Decimal
    material_loss_rate: Decimal
    scrap_recovery_rate: Decimal
    calc_status: str
    audit_status: str
    updated_by: str | None
    created_by: str | None = None
    blank_weight_kg: Decimal | None = None
    finished_total_kg: Decimal | None = None
    scrap_weight_kg: Decimal | None = None
    material_utilization_pct: Decimal | None = None
    steel_price_id: int | None = None
    steel_mill: str | None = None
    steel_ton_price: Decimal | None = None
    scrap_price_id: int | None = None
    scrap_ton_price: Decimal | None = None
    process_fee_id: int | None = None
    process_fee_amount: Decimal | None = None
    die_fee_id: int | None = None
    die_fee_amount: Decimal | None = None
    gauge_fee_id: int | None = None
    gauge_fee_amount: Decimal | None = None
    material_amount_sheet: Decimal | None = None
    loss_scrap_deduction: Decimal | None = None
    process_scrap_deduction: Decimal | None = None
    scrap_amount_sheet: Decimal | None = None
    material_net_per_part: Decimal | None = None
    direct_cost: Decimal | None = None
    finished_finance_fee: Decimal | None = None
    finished_management_fee: Decimal | None = None
    finished_warehouse_packaging_fee: Decimal | None = None
    finished_pretax_profit_fee: Decimal | None = None
    unit_cost: Decimal | None = None
    calc_batch_id: str | None = None
    calc_fail_reason: str | None = None
    formula_version: str | None = None
    calculated_at: datetime | None = None
    remark: str | None = None


class StampingPartCostPatch(TypedDict, total=False):
    """零件核价部分更新（手工改价等）。"""

    unit_cost: Decimal | None
    remark: str | None
    updated_by: str


@dataclass(slots=True)
class StampingPartCostCalcLogCreate:
    """零件核价计算日志新建。"""

    calc_batch_id: str
    year: int
    month: int
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


class StampingPartCostCalcLogPatch(TypedDict, total=False):
    """零件核价计算日志部分更新。"""

    status: str
    total_parts: int
    success_count: int
    failed_count: int
    skipped_approved_count: int
    detail_text: str
    finished_at: datetime
    updated_by: str | None
