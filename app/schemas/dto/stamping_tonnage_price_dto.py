"""
冲次单价 DTO - 内部传输/请求参数
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q3, quantize_money


def quantize_price_per_stroke(value: Any) -> Decimal:
    """解析并量化为 3 位小数 Decimal（禁止以 float 作为业务类型）。"""
    return quantize_money(value, Q3)


class StampingTonnagePriceCreate(BaseModel):
    """冲次单价创建请求"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    year: int = Field(..., ge=2000, le=2100, description="年份")
    tonnage: int = Field(..., ge=1, description="压机吨位(T)")
    price_per_stroke: Decimal = Field(..., ge=0, description="单冲次价格(元)，Decimal 保留3位小数")

    @field_validator("price_per_stroke", mode="before")
    @classmethod
    def _coerce_price(cls, value: Any) -> Decimal:
        return quantize_price_per_stroke(value)


class StampingTonnagePriceUpdate(BaseModel):
    """冲次单价更新请求"""

    price_per_stroke: Decimal = Field(..., ge=0, description="单冲次价格(元)，Decimal 保留3位小数")

    @field_validator("price_per_stroke", mode="before")
    @classmethod
    def _coerce_price(cls, value: Any) -> Decimal:
        return quantize_price_per_stroke(value)


class StampingTonnagePriceQuery(BaseModel):
    """冲次单价查询参数"""

    location: str | None = Field(None, description="采购基地")
    year: int | None = Field(None, description="年份")
    audit_status: str | None = Field(None, description="审核状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")


class StampingTonnagePriceScopeDTO(BaseModel):
    """范围必填：基地 + 年度（上传 / 删除 / 审核 / 反审核共用）"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地（必填）")
    year: int = Field(..., ge=2000, le=2100, description="年度（必填）")


class StampingTonnagePriceBatchDeleteDTO(StampingTonnagePriceScopeDTO):
    """按基地 + 年度批量删除（仅删未审核；已通过跳过）"""


class StampingTonnagePriceBatchApproveDTO(StampingTonnagePriceScopeDTO):
    """批量审核通过"""

    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class StampingTonnagePriceBatchReverseAuditDTO(StampingTonnagePriceScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")
