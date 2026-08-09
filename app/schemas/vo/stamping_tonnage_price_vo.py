"""
吨位价格 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, field_serializer


def decimal_to_float(value: Union[Decimal, float, None]) -> float | None:
    """Decimal 类型转 float 序列化器工厂"""
    return float(value) if isinstance(value, Decimal) else value


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
