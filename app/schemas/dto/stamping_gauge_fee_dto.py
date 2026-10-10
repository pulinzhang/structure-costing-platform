"""冲压检具费档案 DTO。"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, quantize_money, quantize_positive_whole
from app.models.stamping.gauge_fee import STATUS_EFFECTIVE, STATUS_INVALID

_ALLOWED_STATUS = frozenset({STATUS_EFFECTIVE, STATUS_INVALID})


def _strip(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _require_status(value: object) -> str:
    text = _strip(value)
    if not text:
        raise ValueError("状态不能为空")
    if text not in _ALLOWED_STATUS:
        raise ValueError("状态须为 effective 或 invalid")
    return text


class StampingGaugeFeeQuery(BaseModel):
    location: str | None = None
    vehicle_model: str | None = None
    part_number: str | None = None
    status: str | None = None
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)

    @field_validator("location", "vehicle_model", "part_number", mode="before")
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip(value)

    @field_validator("status", mode="before")
    @classmethod
    def optional_status(cls, value: object) -> str | None:
        text = _strip(value)
        if text is None:
            return None
        return _require_status(text)


class StampingGaugeFeeUpdate(BaseModel):
    gauge_fee: Decimal | None = None
    allocation_qty: Decimal | None = None
    status: str | None = None

    @field_validator("gauge_fee", mode="before")
    @classmethod
    def coerce_optional_fee(cls, value: object) -> Decimal | None:
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return None
        return quantize_money(value, Q4)

    @field_validator("allocation_qty", mode="before")
    @classmethod
    def coerce_optional_qty(cls, value: object) -> Decimal | None:
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return None
        number = quantize_positive_whole(value, label="分摊万台")
        return number

    @field_validator("status", mode="before")
    @classmethod
    def coerce_optional_status(cls, value: object) -> str | None:
        text = _strip(value)
        if text is None:
            return None
        return _require_status(text)


@dataclass(slots=True)
class StampingGaugeFeeInsert:
    location: str
    vehicle_model: str
    part_number: str
    part_name: str | None
    gauge_fee: Decimal
    allocation_qty: Decimal
    status: str
    created_by: str
    updated_by: str


class StampingGaugeFeePatch(TypedDict, total=False):
    gauge_fee: Decimal
    allocation_qty: Decimal
    status: str
    updated_by: str
