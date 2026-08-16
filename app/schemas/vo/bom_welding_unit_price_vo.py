"""
焊接工费单价 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, field_serializer


def decimal_to_float(value: Union[Decimal, float, None]) -> float | None:
    """Decimal 类型转 float 序列化器"""
    return float(value) if isinstance(value, Decimal) else value


class BomWeldingUnitPriceResponse(BaseModel):
    """焊接工费单价响应 VO"""

    id: int
    location: str
    year: int
    item_name: str
    unit: str
    unit_price: float
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Union[Decimal, float]) -> float:
        result = decimal_to_float(value)
        return 0.0 if result is None else result

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class BomWeldingUnitPriceBulkUpsertResponse(BaseModel):
    """焊接工费单价批量写入响应 VO"""

    created: list[BomWeldingUnitPriceResponse]
    updated: list[BomWeldingUnitPriceResponse]
    failed: list[str]
    created_count: int
    updated_count: int
    failed_count: int


class BomWeldingUnitPriceCopyYearResponse(BaseModel):
    """焊接工费单价跨年复制响应 VO"""

    location: str
    source_year: int
    target_year: int
    created_count: int
    skipped_count: int
    failed: list[str]


class BomWeldingUnitPriceImportResultVO(BaseModel):
    """焊接工费单价 Excel 导入结果 VO"""

    location: str
    year: int
    created_count: int
    updated_count: int
    total_count: int
    skipped_count: int = 0
    warnings: list[str] = []
    message: str = ""


class BomWeldingUnitPriceBatchDeleteResultVO(BaseModel):
    """焊接工费单价按基地+年度批量删除结果 VO"""

    location: str
    year: int
    deleted_count: int
    message: str = ""
