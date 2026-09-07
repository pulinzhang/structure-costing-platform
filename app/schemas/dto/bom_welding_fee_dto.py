"""
BOM 焊接费 DTO - 请求参数 / 仓库写入载荷
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, TypedDict

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, optional_quantize_money


def coerce_level_list(value: object) -> list[int] | None:
    """查询/批量入参：``0,1`` / ``[0,1]`` / 单个整数 → 去重后的层级列表。"""
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return [value] if value >= 0 else None
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip() != ""]
        numbers = [int(part) for part in parts]
        return sorted(set(numbers)) or None
    if isinstance(value, list | tuple):
        collected: list[int] = []
        for item in value:
            if isinstance(item, int):
                collected.append(item)
                continue
            text = str(item).strip()
            if not text:
                continue
            collected.extend(int(part) for part in text.split(",") if part.strip() != "")
        return sorted(set(collected)) or None
    return None


def resolve_welding_fee_levels(
    *,
    level: int | None = None,
    levels: list[int] | None = None,
) -> list[int] | None:
    """单层 ``level`` 与多层 ``levels`` 合并；都空则不过滤。"""
    selected: list[int] = []
    if level is not None:
        selected.append(int(level))
    if levels:
        selected.extend(int(item) for item in levels)
    if not selected:
        return None
    return sorted(set(selected))


class BomWeldingFeeScopeDTO(BaseModel):
    """范围必填：年度 + 基地 + 车型 + BOM 版本"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    location: str = Field(..., min_length=1, description="基地")
    vehicle_model: str = Field(..., min_length=1, description="项目")
    bom_version: str = Field(..., min_length=1, description="材料清单版本")


class BomWeldingFeeCalcDTO(BomWeldingFeeScopeDTO):
    """焊接费计算请求。levels 为空则计算拆解中出现的全部层级。"""

    levels: list[int] | None = Field(
        default=None,
        description="要计算的树层级；省略或空列表表示全部层级",
    )


class BomWeldingFeeQuery(BaseModel):
    """焊接费列表查询参数"""

    year: int | None = Field(None, description="年度")
    location: str | None = Field(None, description="基地")
    vehicle_model: str | None = Field(None, description="项目")
    bom_version: str | None = Field(None, description="材料清单版本")
    part_number: str | None = Field(None, description="零件号")
    audit_status: str | None = Field(None, description="审核状态")
    calc_status: str | None = Field(None, description="计算状态")
    level: int | None = Field(None, ge=0, description="树层级（单层；与 levels 同时传时合并）")
    levels: list[int] | None = Field(
        None,
        description="树层级（可多选，如 0,1 表示 L0+L1）",
    )
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=500, description="每页条数")

    @field_validator("levels", mode="before")
    @classmethod
    def _coerce_levels(cls, value: object) -> list[int] | None:
        return coerce_level_list(value)


class BomWeldingFeeBatchApproveDTO(BomWeldingFeeScopeDTO):
    """批量审核通过"""

    level: int | None = Field(None, ge=0, description="仅处理该层级；与 levels 同时传时合并")
    levels: list[int] | None = Field(None, description="仅处理这些层级，如 0,1")
    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")

    @field_validator("levels", mode="before")
    @classmethod
    def _coerce_levels(cls, value: object) -> list[int] | None:
        return coerce_level_list(value)


class BomWeldingFeeBatchReverseAuditDTO(BomWeldingFeeScopeDTO):
    """批量反审核"""

    level: int | None = Field(None, ge=0, description="仅处理该层级；与 levels 同时传时合并")
    levels: list[int] | None = Field(None, description="仅处理这些层级，如 0,1")
    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")

    @field_validator("levels", mode="before")
    @classmethod
    def _coerce_levels(cls, value: object) -> list[int] | None:
        return coerce_level_list(value)


class BomWeldingFeeBatchDeleteDTO(BomWeldingFeeScopeDTO):
    """批量删除（仅删未审核；已通过跳过）"""

    level: int | None = Field(None, ge=0, description="仅处理该层级；与 levels 同时传时合并")
    levels: list[int] | None = Field(None, description="仅处理这些层级，如 0,1")

    @field_validator("levels", mode="before")
    @classmethod
    def _coerce_levels(cls, value: object) -> list[int] | None:
        return coerce_level_list(value)


class BomWeldingFeeUpdateDTO(BaseModel):
    """其它费用与备注"""

    other_fee: Decimal | None = Field(
        None,
        description="其它费用(元)；可正可负；传 null 表示无其它费用",
    )
    remark: str | None = Field(None, max_length=1000, description="备注（调整理由/原因）")

    @field_validator("other_fee", mode="before")
    @classmethod
    def _coerce_other_fee(cls, value: Any) -> Decimal | None:
        return optional_quantize_money(value, Q4)


@dataclass(slots=True)
class BomWeldingFeeItemPayload:
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
class BomWeldingFeeUpsertPayload:
    """焊接费主表 upsert（含明细 items）。"""

    year: int
    location: str
    vehicle_model: str
    bom_version: str
    level: int
    source_breakdown_node_id: int | None
    part_number: str
    part_name: str | None
    customer_name: str | None
    weld_info_raw: str | None
    process_line_count: int
    matched_line_count: int
    missing_price_count: int
    total_welding_fee: Decimal
    final_welding_fee: Decimal | None
    calc_batch_id: str | None
    calc_status: str
    calc_message: str | None
    audit_status: str
    updated_by: str | None
    created_by: str | None = None
    items: list[BomWeldingFeeItemPayload] = field(default_factory=list)


@dataclass(slots=True)
class BomWeldingFeeCalcLogCreate:
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


class BomWeldingFeeCalcLogPatch(TypedDict, total=False):
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


class WeldingFeePatch(TypedDict, total=False):
    """焊接费部分更新（其它费用等）。"""

    other_fee: Decimal | None
    final_welding_fee: Decimal | None
    remark: str | None
    updated_by: str
