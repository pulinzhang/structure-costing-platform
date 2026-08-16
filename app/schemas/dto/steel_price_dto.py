"""
钢材价格 DTO - 请求参数
"""

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, optional_quantize_money, quantize_money


class SteelPriceQuery(BaseModel):
    """钢材价格查询参数 DTO"""

    year: Optional[int] = Field(None, ge=2000, le=2100, description="年度")
    month: Optional[int] = Field(None, ge=1, le=12, description="月份")
    location: Optional[str] = Field(None, description="采购基地")
    category_name: Optional[str] = Field(None, description="钢种大类")
    grade: Optional[str] = Field(None, description="牌号（模糊匹配）")
    steel_mill: Optional[str] = Field(None, description="钢厂")
    audit_status: Optional[str] = Field(None, description="审核状态")
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
    spec: Optional[str] = Field(None, max_length=100, description="展示规格")
    base_price: Decimal = Field(..., ge=0, description="基准价(元/吨)")
    thickness_adjustment: Decimal = Field(Decimal("0"), description="厚度加减价(元/吨)")
    width_adjustment: Decimal = Field(Decimal("0"), description="宽度加减价(元/吨)")
    zinc_adjustment: Decimal = Field(Decimal("0"), description="锌层加减价(元/吨)")
    processing_fee: Decimal = Field(Decimal("0"), ge=0, description="加工费(元/吨)")
    other_adjustment: Decimal = Field(Decimal("0"), description="其他调整(元/吨)")
    remark: Optional[str] = Field(None, description="备注")

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

    base_price: Optional[Decimal] = Field(None, ge=0, description="基准价(元/吨)")
    thickness_adjustment: Optional[Decimal] = Field(None, description="厚度加减价(元/吨)")
    width_adjustment: Optional[Decimal] = Field(None, description="宽度加减价(元/吨)")
    zinc_adjustment: Optional[Decimal] = Field(None, description="锌层加减价(元/吨)")
    processing_fee: Optional[Decimal] = Field(None, ge=0, description="加工费(元/吨)")
    other_adjustment: Optional[Decimal] = Field(None, description="其他调整(元/吨)")
    spec: Optional[str] = Field(None, max_length=100, description="展示规格")
    remark: Optional[str] = Field(None, description="备注")

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


class SteelPriceAuditDTO(BaseModel):
    """审核通过 / 驳回请求 DTO（审核人取自 current_user）"""

    audit_remark: Optional[str] = Field(None, description="审核意见")


class SteelPriceReverseAuditDTO(BaseModel):
    """反审核请求 DTO（反审核人取自 current_user）"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")


class SteelPriceCalcDTO(BaseModel):
    """钢价批量计算请求 DTO"""

    year: int = Field(..., ge=2000, le=2100, description="核价年度")
    month: int = Field(..., ge=1, le=12, description="核价月份")
    location: str = Field(..., min_length=1, max_length=50, description="生产基地")
    stamping_supplier: Optional[str] = Field(None, max_length=50, description="冲压工厂")
    vehicle_model: Optional[str] = Field(None, max_length=50, description="配套车型")


class SteelPriceBatchDeleteDTO(BaseModel):
    """按筛选条件批量删除钢材价格（年度/月份/基地必填；仅删未审核）"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    category_name: Optional[str] = Field(None, description="钢种大类")
    grade: Optional[str] = Field(None, description="牌号（模糊匹配）")
    steel_mill: Optional[str] = Field(None, description="钢厂")


class SteelPriceBatchApproveDTO(BaseModel):
    """按条件批量审核通过（仅年度/月份/基地，三者必填；审核人取自 current_user）"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    audit_remark: Optional[str] = Field(None, description="审核意见")


class SteelPriceBatchReverseAuditDTO(BaseModel):
    """按条件批量反审核（仅年度/月份/基地，三者必填；反审核人取自 current_user）"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")
