"""冲压检具费档案 VO。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, computed_field, field_serializer

from app.common.money import Q0, Q4, format_money
from app.common.timezone import datetime_to_iso
from app.models.stamping.gauge_fee import STATUS_EFFECTIVE, STATUS_INVALID

_STATUS_LABELS = {
    STATUS_EFFECTIVE: "生效",
    STATUS_INVALID: "失效",
}


class StampingGaugeFeeVO(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    location: str
    vehicle_model: str
    part_number: str
    part_name: str | None = None
    gauge_fee: Decimal
    allocation_qty: Decimal
    status: str
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("gauge_fee")
    def serialize_money(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)

    @field_serializer("allocation_qty")
    def serialize_allocation_qty(self, value: Decimal) -> str:
        return format_money(value, Q0, 0)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    @computed_field
    def status_label(self) -> str:
        return _STATUS_LABELS.get(self.status, self.status)


class StampingGaugeFeeListSummaryVO(BaseModel):
    """列表 HUD：与当前筛选同一套范围。"""

    total_count: int = 0
    effective_count: int = 0
    invalid_count: int = 0
    total_gauge_fee: Decimal = Decimal("0")

    @field_serializer("total_gauge_fee")
    def serialize_gauge_fee(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)


class StampingGaugeFeeListFiltersVO(BaseModel):
    summary: StampingGaugeFeeListSummaryVO


class StampingGaugeFeeFilterVO(BaseModel):
    locations: list[str]
    vehicle_models: list[str]


class StampingGaugeFeeImportResultVO(BaseModel):
    location: str
    vehicle_model: str
    imported_count: int
    message: str


class StampingGaugeFeeScopeDeleteResultVO(BaseModel):
    location: str
    vehicle_model: str
    deleted_count: int
    message: str
