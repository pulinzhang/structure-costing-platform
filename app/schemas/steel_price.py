"""钢材价格请求与响应 DTO。"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_serializer


class SteelPriceQuery(BaseModel):
    """钢材价格分页筛选参数。"""

    year: Optional[int] = Field(None, ge=2000, le=2100, description="年度")
    month: Optional[int] = Field(None, ge=1, le=12, description="月份")
    steel_type: Optional[str] = Field(None, description="钢种")
    grade: Optional[str] = Field(None, description="牌号")
    steel_mill: Optional[str] = Field(None, description="钢厂")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=200, description="每页条数")


class SteelPriceCreate(BaseModel):
    """钢材价格创建请求（前端表单使用）。"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    steel_type: str = Field(..., min_length=1, max_length=50, description="钢种")
    grade: str = Field(..., min_length=1, max_length=100, description="牌号")
    reference_spec: str = Field(..., min_length=1, max_length=100, description="参考规格")
    steel_mill: str = Field(..., min_length=1, max_length=100, description="钢厂")
    bid_price: float = Field(..., ge=0, description="中标价")
    thickness: float = Field(..., ge=0, description="厚度")
    thickness_adjustment: float = Field(..., ge=0, description="厚度加减价")
    processing_fee: float = Field(..., ge=0, description="加工费")
    final_price_per_ton: float = Field(..., ge=0, description="最终价/吨")
    remark: Optional[str] = Field(None, description="备注")


class SteelPriceUpdate(BaseModel):
    """钢材价格更新请求（前端表单使用）。

    业务主键 ``(year, month, grade, thickness)`` 不允许变更，所以仅保留可编辑字段。
    """

    bid_price: float = Field(..., ge=0, description="中标价")
    thickness_adjustment: float = Field(..., ge=0, description="厚度加减价")
    processing_fee: float = Field(..., ge=0, description="加工费")
    final_price_per_ton: float = Field(..., ge=0, description="最终价/吨")
    remark: Optional[str] = Field(None, description="备注")
    steel_type: Optional[str] = Field(None, min_length=1, max_length=50, description="钢种")
    steel_mill: Optional[str] = Field(None, min_length=1, max_length=100, description="钢厂")
    reference_spec: Optional[str] = Field(None, min_length=1, max_length=100, description="参考规格")


class SteelPriceResponse(BaseModel):
    """钢材价格列表响应。"""

    id: int
    year: int
    month: int
    steel_type: str
    grade: str
    reference_spec: str
    steel_mill: str
    bid_price: float
    thickness: float
    thickness_adjustment: float
    processing_fee: float
    final_price_per_ton: float
    remark: str | None
    created_at: datetime
    updated_at: datetime

    @field_serializer(
        "bid_price",
        "thickness",
        "thickness_adjustment",
        "processing_fee",
        "final_price_per_ton",
    )
    def serialize_decimal(self, value: Decimal | float) -> float:
        return float(value)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    model_config = {"from_attributes": True}
