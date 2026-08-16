"""
冲次单价 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_serializer

from app.common.money import Q3, format_money


def format_price_per_stroke(value: Any) -> str:
    """单价序列化为固定 3 位小数字符串，避免 JSON float 精度丢失。"""
    return format_money(value if value is not None else Decimal("0"), Q3, 3)


class StampingTonnagePriceResponse(BaseModel):
    """冲次单价响应 VO（对应 stamping_tonnage_price 表）"""

    id: int
    location: str
    year: int
    tonnage: int
    price_per_stroke: Decimal
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

    @field_serializer("price_per_stroke")
    def serialize_price(self, value: Decimal) -> str:
        return format_price_per_stroke(value)

    @field_serializer("created_at", "updated_at", "audited_at", "reverse_audited_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class StampingTonnagePriceBulkUpsertResponse(BaseModel):
    """冲次单价批量写入响应 VO（与 Excel 导入一致：存在则更新）"""

    created: list[StampingTonnagePriceResponse]
    updated: list[StampingTonnagePriceResponse]
    failed: list[str]
    created_count: int
    updated_count: int
    failed_count: int
    skipped_approved_count: int = 0


class StampingTonnagePriceCopyYearResponse(BaseModel):
    """冲次单价跨年复制响应 VO"""

    location: str
    source_year: int
    target_year: int
    created_count: int
    skipped_count: int
    failed: list[str]


class StampingTonnagePriceImportResultVO(BaseModel):
    """冲次单价 Excel 导入结果 VO"""

    location: str
    year: int
    created_count: int
    updated_count: int
    total_count: int
    skipped_count: int = 0
    warnings: list[str] = []
    message: str = ""


class StampingTonnagePriceBatchDeleteResultVO(BaseModel):
    """冲次单价按基地+年度批量删除结果 VO"""

    location: str
    year: int
    deleted_count: int
    skipped_approved_count: int = 0
    message: str = ""


class StampingTonnagePriceBatchAuditResultVO(BaseModel):
    """按基地+年度批量审核 / 反审核结果"""

    updated_count: int = 0
    skipped_count: int = 0
    location: str
    year: int
