"""
BOM 焊接费 DTO - 请求参数 / 仓库写入载荷
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from pydantic import BaseModel, Field


class BomL0WeldingFeeScopeDTO(BaseModel):
    """范围必填：年度 + 基地 + 车型 + BOM 版本"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    location: str = Field(..., min_length=1, description="基地")
    vehicle_model: str = Field(..., min_length=1, description="车型")
    bom_version: str = Field(..., min_length=1, description="材料清单版本")


class BomL0WeldingFeeCalcDTO(BomL0WeldingFeeScopeDTO):
    """焊接费计算请求"""


class BomL0WeldingFeeQuery(BaseModel):
    """焊接费列表查询参数"""

    year: int | None = Field(None, description="年度")
    location: str | None = Field(None, description="基地")
    vehicle_model: str | None = Field(None, description="车型")
    bom_version: str | None = Field(None, description="材料清单版本")
    part_number: str | None = Field(None, description="零件号")
    audit_status: str | None = Field(None, description="审核状态")
    calc_status: str | None = Field(None, description="计算状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=500, description="每页条数")


class BomL0WeldingFeeBatchApproveDTO(BomL0WeldingFeeScopeDTO):
    """批量审核通过"""

    audit_remark: str | None = Field(None, description="审核意见")


class BomL0WeldingFeeBatchReverseAuditDTO(BomL0WeldingFeeScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")


class BomL0WeldingFeeBatchDeleteDTO(BomL0WeldingFeeScopeDTO):
    """批量删除（仅删未审核；已通过跳过）"""


@dataclass(slots=True)
class BomL0WeldingFeeItemPayload:
    """焊接费工艺明细写入。"""

    line_no: int
    process_token: str | None = None
    standard_process_name: str | None = None
    process_qty: Decimal = Decimal("0")
    process_qty_unit: str | None = None
    unit_price: Decimal | None = None
    unit: str | None = None
    line_fee: Decimal | None = None
    match_status: str = "unmapped"
    source_breakdown_line_id: int | None = None
    remark: str | None = None


@dataclass(slots=True)
class BomL0WeldingFeeUpsertPayload:
    """焊接费主表 upsert（含明细 items）。"""

    year: int
    location: str
    vehicle_model: str
    bom_version: str
    source_breakdown_node_id: int | None
    part_number: str
    part_name: str | None
    customer_name: str | None
    weld_info_raw: str | None
    process_line_count: int
    matched_line_count: int
    missing_price_count: int
    total_l0_welding_fee: Decimal
    calc_batch_id: str | None
    calc_status: str
    calc_message: str | None
    audit_status: str
    updated_by: str | None
    created_by: str | None = None
    items: list[BomL0WeldingFeeItemPayload] = field(default_factory=list)


@dataclass(slots=True)
class BomL0WeldingFeeCalcLogCreate:
    """焊接费计算日志新建。"""

    calc_batch_id: str
    year: int
    location: str
    vehicle_model: str
    bom_version: str
    status: str
    detail_text: str
    started_at: datetime
    operator_id: int | None = None
    operator_name: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


class BomL0WeldingFeeCalcLogPatch(TypedDict, total=False):
    """焊接费计算日志部分更新。"""

    status: str
    l0_count: int
    created_count: int
    updated_count: int
    skipped_approved_count: int
    failed_count: int
    missing_price_count: int
    detail_text: str
    finished_at: datetime
    updated_by: str | None

