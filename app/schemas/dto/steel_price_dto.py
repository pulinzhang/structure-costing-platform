"""
钢材价格 DTO - 请求参数 / Repository 写入载荷
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, TypedDict

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, optional_quantize_money, quantize_money


class SteelPriceQuery(BaseModel):
    """钢材价格查询参数 DTO"""

    year: int | None = Field(None, ge=2000, le=2100, description="年度")
    month: int | None = Field(None, ge=1, le=12, description="月份")
    location: str | None = Field(None, description="采购基地")
    category_name: str | None = Field(None, description="钢种大类")
    grade: str | None = Field(None, description="牌号（模糊匹配）")
    steel_mill: str | None = Field(None, description="钢厂")
    audit_status: str | None = Field(None, description="审核状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=200, description="每页条数")


class SteelPriceCreate(BaseModel):
    """钢材价格创建请求 DTO（手工录入，落库为 manual 匹配）"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    steel_mill: str = Field(..., min_length=1, max_length=100, description="钢厂")
    category_name: str = Field(..., min_length=1, max_length=50, description="钢种大类")
    grade: str = Field(..., min_length=1, max_length=100, description="牌号")
    thickness: Decimal = Field(..., ge=0, description="料厚(mm)")
    width: Decimal = Field(..., ge=0, description="宽度(mm)")
    spec: str | None = Field(None, max_length=100, description="展示规格")
    base_price: Decimal = Field(..., ge=0, description="基准价(元/吨)")
    thickness_adjustment: Decimal = Field(Decimal("0"), description="厚度加减价(元/吨)")
    width_adjustment: Decimal = Field(Decimal("0"), description="宽度加减价(元/吨)")
    zinc_adjustment: Decimal = Field(Decimal("0"), description="锌层加减价(元/吨)")
    processing_fee: Decimal = Field(Decimal("0"), ge=0, description="加工费(元/吨)")
    other_adjustment: Decimal = Field(Decimal("0"), description="其他调整(元/吨)")
    remark: str | None = Field(None, description="备注")

    @field_validator("thickness", "width", "base_price", "processing_fee", mode="before")
    @classmethod
    def _coerce_nonneg_q4(cls, value: Any) -> Decimal:
        return quantize_money(value, Q4)

    @field_validator(
        "thickness_adjustment",
        "width_adjustment",
        "zinc_adjustment",
        "other_adjustment",
        mode="before",
    )
    @classmethod
    def _coerce_signed_q4(cls, value: Any) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return quantize_money(value, Q4, allow_negative=True)


class SteelPriceUpdate(BaseModel):
    """钢材价格更新请求 DTO（业务主键不可改；approved 时拒绝）"""

    base_price: Decimal | None = Field(None, ge=0, description="基准价(元/吨)")
    thickness_adjustment: Decimal | None = Field(None, description="厚度加减价(元/吨)")
    width_adjustment: Decimal | None = Field(None, description="宽度加减价(元/吨)")
    zinc_adjustment: Decimal | None = Field(None, description="锌层加减价(元/吨)")
    processing_fee: Decimal | None = Field(None, ge=0, description="加工费(元/吨)")
    other_adjustment: Decimal | None = Field(None, description="其他调整(元/吨)")
    spec: str | None = Field(None, max_length=100, description="展示规格")
    remark: str | None = Field(None, description="备注")

    @field_validator("base_price", "processing_fee", mode="before")
    @classmethod
    def _coerce_nonneg_q4(cls, value: Any) -> Decimal | None:
        return optional_quantize_money(value, Q4)

    @field_validator(
        "thickness_adjustment",
        "width_adjustment",
        "zinc_adjustment",
        "other_adjustment",
        mode="before",
    )
    @classmethod
    def _coerce_signed_q4(cls, value: Any) -> Decimal | None:
        return optional_quantize_money(value, Q4, allow_negative=True)


class SteelPriceCalcDTO(BaseModel):
    """钢价批量计算请求 DTO"""

    year: int = Field(..., ge=2000, le=2100, description="核价年度")
    month: int = Field(..., ge=1, le=12, description="核价月份")
    location: str = Field(..., min_length=1, max_length=50, description="生产基地")


class SteelPriceBatchDeleteDTO(BaseModel):
    """按筛选条件批量删除钢材价格（年度/月份/基地必填；仅删未审核）"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    category_name: str | None = Field(None, description="钢种大类")
    grade: str | None = Field(None, description="牌号（模糊匹配）")
    steel_mill: str | None = Field(None, description="钢厂")


class SteelPriceBatchApproveDTO(BaseModel):
    """按条件批量审核通过（仅年度/月份/基地，三者必填；审核人取自 current_user）"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class SteelPriceBatchReverseAuditDTO(BaseModel):
    """按条件批量反审核（仅年度/月份/基地，三者必填；反审核人取自 current_user）"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")


@dataclass(slots=True)
class SteelPriceWrite:
    """钢材价格插入（手工录入 / 计算落库）。"""

    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thickness: Decimal
    width: Decimal
    base_price: Decimal
    final_price_per_ton: Decimal
    calc_batch_id: str
    match_status: str
    calculated_at: datetime
    spec: str | None = None
    thickness_adjustment: Decimal = Decimal("0")
    width_adjustment: Decimal = Decimal("0")
    zinc_adjustment: Decimal = Decimal("0")
    processing_fee: Decimal = Decimal("0")
    other_adjustment: Decimal = Decimal("0")
    base_price_id: int | None = None
    base_excel_filename: str | None = None
    base_sheet_name: str | None = None
    base_excel_row: int | None = None
    base_excel_col: int | None = None
    thickness_policy_id: int | None = None
    thickness_ladder_item_id: int | None = None
    thickness_excel_filename: str | None = None
    thickness_sheet_name: str | None = None
    thickness_excel_row: int | None = None
    thickness_excel_col: int | None = None
    width_policy_id: int | None = None
    width_ladder_item_id: int | None = None
    width_excel_filename: str | None = None
    width_sheet_name: str | None = None
    width_excel_row: int | None = None
    width_excel_col: int | None = None
    zinc_policy_id: int | None = None
    zinc_ladder_item_id: int | None = None
    zinc_excel_filename: str | None = None
    zinc_sheet_name: str | None = None
    zinc_excel_row: int | None = None
    zinc_excel_col: int | None = None
    calc_status: str = "success"
    calc_message: str | None = None
    formula_version: str = "v1"
    audit_status: str = "pending"
    audited_by: str | None = None
    audited_at: datetime | None = None
    audit_remark: str | None = None
    reverse_audited_by: str | None = None
    reverse_audited_at: datetime | None = None
    reverse_audit_remark: str | None = None
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


class SteelPricePatch(TypedDict, total=False):
    """钢材价格部分更新（手工改价 / 审核 / 计算覆盖）。"""

    spec: str | None
    base_price: Decimal
    thickness_adjustment: Decimal
    width_adjustment: Decimal
    zinc_adjustment: Decimal
    processing_fee: Decimal
    other_adjustment: Decimal
    final_price_per_ton: Decimal
    remark: str | None
    calc_batch_id: str
    match_status: str
    calc_status: str
    calc_message: str | None
    formula_version: str
    calculated_at: datetime
    audit_status: str
    audited_by: str | None
    audited_at: datetime | None
    audit_remark: str | None
    reverse_audited_by: str | None
    reverse_audited_at: datetime | None
    reverse_audit_remark: str | None
    updated_by: str | None


@dataclass(slots=True)
class SteelPriceCalcLogCreate:
    """钢价计算日志新建。"""

    calc_batch_id: str
    year: int
    month: int
    location: str
    status: str
    detail_text: str
    started_at: datetime
    material_count: int = 0
    enriched_count: int = 0
    no_base_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_approved_count: int = 0
    failed_count: int = 0
    finished_at: datetime | None = None
    operator_id: int | None = None
    operator_name: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


class SteelPriceCalcLogPatch(TypedDict, total=False):
    """钢价计算日志部分更新。"""

    status: str
    material_count: int
    enriched_count: int
    no_base_count: int
    created_count: int
    updated_count: int
    skipped_approved_count: int
    failed_count: int
    detail_text: str
    finished_at: datetime
    updated_by: str | None
