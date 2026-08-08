"""
吨位价格 VO - 请求和响应的数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_serializer


def decimal_to_float(value: Union[Decimal, float, None]) -> float | None:
    """Decimal 类型转 float 序列化器工厂"""
    return float(value) if isinstance(value, Decimal) else value


class StampingTonnagePriceCreate(BaseModel):
    """吨位价格创建请求"""
    year: int = Field(..., ge=2000, le=2100, description="年份")
    tonnage: int = Field(..., ge=1, description="压机吨位(T)")
    price_per_stroke: float = Field(..., ge=0, description="单冲次价格(元)")


class StampingTonnagePriceUpdate(BaseModel):
    """吨位价格更新请求"""
    price_per_stroke: float = Field(..., ge=0, description="单冲次价格(元)")


class StampingTonnagePriceResponse(BaseModel):
    """吨位价格响应 VO"""
    id: int
    year: int
    tonnage: int
    price_per_stroke: float
    created_at: datetime | None
    updated_at: datetime | None

    @field_serializer("price_per_stroke")
    def serialize_price(self, value: Union[Decimal, float]) -> float:
        return decimal_to_float(value)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class StampingTonnagePriceQuery(BaseModel):
    """吨位价格查询参数"""
    year: Optional[int] = Field(None, description="年份")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")


class StampingTonnagePriceBulkCreate(BaseModel):
    """吨位价格批量创建请求"""
    items: List[StampingTonnagePriceCreate] = Field(..., min_length=1, description="批量创建项")


class StampingTonnagePriceCopyTemplate(BaseModel):
    """从指定年份复制价格模板"""
    source_year: int = Field(..., ge=2000, le=2100, description="源年份")
    target_year: int = Field(..., ge=2000, le=2100, description="目标年份")
