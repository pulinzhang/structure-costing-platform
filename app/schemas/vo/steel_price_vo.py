"""
钢材价格 VO - 返回给前端的数据结构
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_serializer


class SteelPriceResponse(BaseModel):
    """钢材价格响应 VO"""

    model_config = {"from_attributes": True}

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
    remark: str | None = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_serializer(
        "bid_price",
        "thickness",
        "thickness_adjustment",
        "processing_fee",
        "final_price_per_ton",
    )
    def serialize_decimal(self, value):
        return float(value)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value):
        return value.isoformat() if value else None


class SteelPriceImportResultResponse(BaseModel):
    """钢材价格导入结果响应"""
    filename: str
    imported_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    periods: list[str] = []
    warnings: Optional[list[str]] = None
