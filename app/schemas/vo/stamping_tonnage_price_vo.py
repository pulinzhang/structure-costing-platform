"""
冲次费率 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, field_serializer


def decimal_to_float(value: Union[Decimal, float, None]) -> float | None:
    """Decimal 类型转 float 序列化器"""
    return float(value) if isinstance(value, Decimal) else value


class StampingTonnagePriceResponse(BaseModel):
    """冲次费率响应 VO（对应 stamping_tonnage_prices 表）"""
    id: int
    year: int
    tonnage: int
    price_per_stroke: float
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("price_per_stroke")
    def serialize_price(self, value: Union[Decimal, float]) -> float:
        return decimal_to_float(value)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class StampingTonnagePriceBulkCreateResponse(BaseModel):
    """冲次费率批量创建响应 VO"""
    created: list[StampingTonnagePriceResponse]
    skipped: list[StampingTonnagePriceResponse]
    failed: list[str]
    created_count: int
    skipped_count: int
    failed_count: int


class StampingTonnagePriceCopyYearResponse(BaseModel):
    """冲次费率跨年复制响应 VO"""
    source_year: int
    target_year: int
    created_count: int
    skipped_count: int
    failed: list[str]
