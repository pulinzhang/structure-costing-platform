"""
BOM 年度零件价 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_serializer, field_validator

from app.common.money import Q4, format_money
from app.common.timezone import datetime_to_iso
from app.schemas.common.batch_result import BatchAuditCountsVO, BatchDeleteCountsVO


def format_unit_price_decimal(value: Any) -> str:
    """单价序列化为固定 4 位小数字符串，避免 JSON float 精度丢失。"""
    return format_money(value if value is not None else Decimal("0"), Q4, 4)


class BomAnnualPartPriceResponse(BaseModel):
    """年度零件价响应 VO"""

    id: int
    location: str
    year: int
    part_number: str
    part_name: str | None = None
    specification: str | None = None
    purchase_unit: str | None = None
    purchase_unit_price: Decimal | None = None
    conversion_factor: int = 1
    unit: str
    unit_price: Decimal
    supply_type: str
    supplier_name: str | None = None
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

    @field_validator("conversion_factor", mode="before")
    @classmethod
    def _coerce_conversion_factor(cls, value: Any) -> int:
        if value is None or value == "":
            return 1
        return int(value)

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Decimal) -> str:
        return format_unit_price_decimal(value)

    @field_serializer("purchase_unit_price")
    def serialize_purchase_unit_price(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format_money(value, Q4, 4)

    @field_serializer("conversion_factor")
    def serialize_conversion_factor(self, value: int) -> str:
        return str(int(value))

    @field_serializer("created_at", "updated_at", "audited_at", "reverse_audited_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class BomAnnualPartPriceImportResultVO(BaseModel):
    """年度零件价 Excel 导入结果 VO"""

    location: str
    year: int
    created_count: int
    updated_count: int
    total_count: int
    skipped_count: int = 0
    skipped_approved_count: int = 0
    warnings: list[str] = []
    message: str = ""


class BomAnnualPartPriceBatchDeleteResultVO(BatchDeleteCountsVO):
    """年度零件价按基地+年度批量删除结果 VO"""

    location: str
    year: int
    message: str = ""


class BomAnnualPartPriceBatchAuditResultVO(BatchAuditCountsVO):
    """按基地+年度批量审核 / 反审核结果"""

    location: str
    year: int
