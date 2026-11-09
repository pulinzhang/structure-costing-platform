"""费用档案 VO。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.money import Q6, format_money
from app.common.timezone import datetime_to_iso


class FeeArchiveVO(BaseModel):
    """费用档案一行。计费率是小数字符串。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    charge_basis: str
    charge_rate: Decimal
    sort_order: int
    is_enabled: bool
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("charge_rate")
    def serialize_rate(self, value: Decimal) -> str:
        return format_money(value, Q6, 6)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)
