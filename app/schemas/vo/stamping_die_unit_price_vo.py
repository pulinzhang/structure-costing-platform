"""冲压模具单价档案 VO。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, computed_field, field_serializer

from app.common.money import Q0, Q4, format_money
from app.common.timezone import datetime_to_iso
from app.models.stamping.die_unit_price import STATUS_EFFECTIVE, STATUS_INVALID

_STATUS_LABELS = {
    STATUS_EFFECTIVE: "生效",
    STATUS_INVALID: "失效",
}


class StampingDieUnitPriceVO(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    location: str
    vehicle_model: str
    steel_plate_unit_price: Decimal
    progressive_die_unit_price: Decimal
    allocation_qty: Decimal
    status: str
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("steel_plate_unit_price", "progressive_die_unit_price")
    def serialize_price(self, value: Decimal) -> str:
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


class StampingDieUnitPriceFilterVO(BaseModel):
    locations: list[str]
    vehicle_models: list[str]
