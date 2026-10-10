"""
冲次单价 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.money import Q3, format_money
from app.common.timezone import datetime_to_iso
from app.schemas.common.batch_result import BatchAuditCountsVO, BatchDeleteCountsVO


def format_price_per_stroke(value: object) -> str:
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
        return datetime_to_iso(value)

    model_config = ConfigDict(from_attributes=True)


class StampingTonnagePriceBulkUpsertResponse(BaseModel):
    """冲次单价批量写入响应 VO（与 Excel 导入一致：存在则更新）"""

    created: list[StampingTonnagePriceResponse]
    updated: list[StampingTonnagePriceResponse]
    failed: list[str]
    created_count: int
    updated_count: int
    failed_count: int
    skipped_approved_count: int = 0
    message: str = ""


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


class StampingTonnagePriceBatchDeleteResultVO(BatchDeleteCountsVO):
    """冲次单价按基地+年度批量删除结果 VO"""

    location: str
    year: int
    message: str = ""


class StampingTonnagePriceBatchAuditResultVO(BatchAuditCountsVO):
    """按基地+年度批量审核 / 反审核结果"""

    location: str
    year: int
