"""
焊接工费单价 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_serializer

from app.common.money import Q4, format_money


def format_unit_price_decimal(value: Any) -> str:
    """单价序列化为固定 4 位小数字符串，避免 JSON float 精度丢失。"""
    return format_money(value if value is not None else Decimal("0"), Q4, 4)


class BomWeldingUnitPriceResponse(BaseModel):
    """焊接工费单价响应 VO"""

    id: int
    location: str
    year: int
    item_name: str
    unit: str
    unit_price: Decimal
    remark: str | None = None
    audit_status: str = "pending"
    audited_by: str | None = None
    audited_at: datetime | None = None
    audit_remark: str | None = None
    reverse_audited_by: str | None = None
    reverse_audited_at: datetime | None = None
    reverse_audit_remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Decimal) -> str:
        return format_unit_price_decimal(value)

    @field_serializer("created_at", "updated_at", "audited_at", "reverse_audited_at")
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
    skipped_approved_count: int = 0


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
    skipped_approved_count: int = 0
    message: str = ""


class BomWeldingUnitPriceBatchAuditResultVO(BaseModel):
    """按基地+年度批量审核 / 反审核结果"""

    updated_count: int = 0
    skipped_count: int = 0
    location: str
    year: int
