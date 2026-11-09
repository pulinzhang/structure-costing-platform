"""计费管理 VO。名称和计费率从两本字典带出。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_serializer

from app.common.money import Q6, format_money
from app.common.timezone import datetime_to_iso


class AssemblyCategoryBillingVO(BaseModel):
    """一条计费对照。计费率只读，来自费用档案。"""

    id: int
    assembly_category_id: int
    assembly_category_code: str
    assembly_category_name: str
    assembly_category_enabled: bool
    fee_archive_id: int
    fee_code: str
    fee_name: str
    fee_enabled: bool
    charge_basis: str
    charge_rate: Decimal
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


class CategoryBillingSelectionVO(BaseModel):
    """某个分类当前勾选的费用。一次保存的返回。"""

    assembly_category_id: int
    assembly_category_name: str
    assembly_category_enabled: bool
    items: list[AssemblyCategoryBillingVO]
