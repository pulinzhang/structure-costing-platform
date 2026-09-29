"""
BOM 年度零件价 DTO - 内部传输/请求参数
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, optional_quantize_money, quantize_money
from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
)
from app.parsers.bom.annual_part_price_parser import parse_conversion_factor


def quantize_unit_price(value: Any) -> Decimal:
    """解析并量化为 4 位小数 Decimal（禁止以 float 作为业务类型）。"""
    return quantize_money(value, Q4)


def normalize_supply_type(value: Any) -> str:
    """原供货类型：原文入库，仅做去空白。"""
    if value is None:
        raise ValueError("原供货类型不能为空")
    text = str(value).strip()
    if not text:
        raise ValueError("原供货类型不能为空")
    if len(text) > 50:
        raise ValueError("原供货类型最长 50 字符")
    return text


class BomAnnualPartPriceCreate(BaseModel):
    """年度零件价创建请求"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="定价年度")
    part_number: str = Field(..., min_length=1, max_length=50, description="零件号")
    part_name: str | None = Field(None, max_length=200, description="零件名称")
    specification: str | None = Field(None, max_length=100, description="规格（展示，不取价）")
    purchase_unit: str | None = Field(None, max_length=20, description="采购单位")
    purchase_unit_price: Decimal | None = Field(None, ge=0, description="采购单价")
    conversion_factor: Decimal = Field(
        default=Decimal("1"),
        description="转换系数，>0，最多6位小数；1采购单位=N核价单位；核价单价=采购单价÷系数",
    )
    unit: str = Field("pcs", min_length=1, max_length=20, description="核价单位")
    unit_price: Decimal = Field(
        ...,
        ge=0,
        description="核价单价(元/核价单位)，≥0；为 0 表示成品核价不计入该件（如结构胶）",
    )
    supply_type: str = Field(..., min_length=1, max_length=50, description="原供货类型")
    supplier_name: str | None = Field(None, max_length=100, description="供应商")
    remark: str | None = Field(None, description="备注")

    @field_validator("supply_type", mode="before")
    @classmethod
    def _coerce_supply_type(cls, value: Any) -> str:
        return normalize_supply_type(value)

    @field_validator("purchase_unit_price", mode="before")
    @classmethod
    def _coerce_purchase_unit_price(cls, value: Any) -> Decimal | None:
        return optional_quantize_money(value, Q4)

    @field_validator("conversion_factor", mode="before")
    @classmethod
    def _coerce_conversion_factor(cls, value: Any) -> Decimal:
        return parse_conversion_factor(value)

    @field_validator("unit_price", mode="before")
    @classmethod
    def _coerce_unit_price(cls, value: Any) -> Decimal:
        return quantize_unit_price(value)


class BomAnnualPartPriceUpdate(BaseModel):
    """年度零件价更新请求（exclude_unset 写入）"""

    part_name: str | None = Field(None, max_length=200, description="零件名称")
    specification: str | None = Field(None, max_length=100, description="规格（展示，不取价）")
    purchase_unit: str | None = Field(None, max_length=20, description="采购单位")
    purchase_unit_price: Decimal | None = Field(None, ge=0, description="采购单价")
    conversion_factor: Decimal | None = Field(
        None,
        description="转换系数，>0，最多6位小数",
    )
    unit: str | None = Field(None, min_length=1, max_length=20, description="核价单位")
    unit_price: Decimal = Field(
        ...,
        ge=0,
        description="核价单价(元/核价单位)，≥0；为 0 表示成品核价不计入该件（如结构胶）",
    )
    supply_type: str | None = Field(None, min_length=1, max_length=50, description="原供货类型")
    supplier_name: str | None = Field(None, max_length=100, description="供应商")
    remark: str | None = Field(None, description="备注")

    @field_validator("supply_type", mode="before")
    @classmethod
    def _coerce_supply_type(cls, value: Any) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return normalize_supply_type(value)

    @field_validator("purchase_unit_price", mode="before")
    @classmethod
    def _coerce_purchase_unit_price(cls, value: Any) -> Decimal | None:
        return optional_quantize_money(value, Q4)

    @field_validator("conversion_factor", mode="before")
    @classmethod
    def _coerce_conversion_factor(cls, value: Any) -> Decimal | None:
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return None
        return parse_conversion_factor(value)

    @field_validator("unit_price", mode="before")
    @classmethod
    def _coerce_unit_price(cls, value: Any) -> Decimal:
        return quantize_unit_price(value)


class BomAnnualPartPriceQuery(BaseModel):
    """年度零件价查询参数"""

    location: str | None = Field(None, description="采购基地")
    year: int | None = Field(None, description="定价年度")
    audit_status: str | None = Field(None, description="审核状态")
    keyword: str | None = Field(None, max_length=100, description="零件号或名称模糊搜索（OR）")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")


class BomAnnualPartPriceScopeDTO(BaseModel):
    """范围必填：基地 + 年度（上传 / 删除 / 审核 / 反审核共用）"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地（必填）")
    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="年度（必填）")


class BomAnnualPartPriceBatchDeleteDTO(BomAnnualPartPriceScopeDTO):
    """按基地 + 年度批量删除（仅删未审核；已通过跳过）"""


class BomAnnualPartPriceBatchApproveDTO(BomAnnualPartPriceScopeDTO):
    """批量审核通过"""

    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class BomAnnualPartPriceBatchReverseAuditDTO(BomAnnualPartPriceScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")
