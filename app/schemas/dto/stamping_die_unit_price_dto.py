"""冲压模具单价档案 DTO。"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, quantize_money, quantize_positive_whole
from app.models.stamping.die_unit_price import STATUS_EFFECTIVE, STATUS_INVALID

_ALLOWED_STATUS = frozenset({STATUS_EFFECTIVE, STATUS_INVALID})
DEFAULT_ALLOCATION_QTY = Decimal("10")


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


def _require_allocation_qty(value: object) -> Decimal:
    return quantize_positive_whole(value, label="分摊万台")


class StampingDieUnitPriceQuery(BaseModel):
    location: str | None = None
    vehicle_model: str | None = None
    status: str | None = None
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)

    @field_validator("location", "vehicle_model", mode="before")
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


class StampingDieUnitPriceCreate(BaseModel):
    location: str = Field(..., min_length=1, max_length=50)
    vehicle_model: str = Field(..., min_length=1, max_length=50)
    steel_plate_unit_price: Decimal
    progressive_die_unit_price: Decimal
    allocation_qty: Decimal = Field(default=DEFAULT_ALLOCATION_QTY)
    status: str = Field(STATUS_EFFECTIVE)

    @field_validator("location", "vehicle_model", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> str:
        text = _strip(value)
        if not text:
            raise ValueError("不能为空")
        return text

    @field_validator("steel_plate_unit_price", "progressive_die_unit_price", mode="before")
    @classmethod
    def coerce_price(cls, value: object) -> Decimal:
        return quantize_money(value, Q4)

    @field_validator("allocation_qty", mode="before")
    @classmethod
    def coerce_qty(cls, value: object) -> Decimal:
        return _require_allocation_qty(value)

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, value: object) -> str:
        return _require_status(value)


class StampingDieUnitPriceUpdate(BaseModel):
    location: str | None = None
    vehicle_model: str | None = None
    steel_plate_unit_price: Decimal | None = None
    progressive_die_unit_price: Decimal | None = None
    allocation_qty: Decimal | None = None
    status: str | None = None

    @field_validator("location", "vehicle_model", mode="before")
    @classmethod
    def strip_optional_scope(cls, value: object) -> str | None:
        return _strip(value)

    @field_validator("steel_plate_unit_price", "progressive_die_unit_price", mode="before")
    @classmethod
    def coerce_optional_price(cls, value: object) -> Decimal | None:
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return None
        return quantize_money(value, Q4)

    @field_validator("allocation_qty", mode="before")
    @classmethod
    def coerce_optional_qty(cls, value: object) -> Decimal | None:
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return None
        return _require_allocation_qty(value)

    @field_validator("status", mode="before")
    @classmethod
    def coerce_optional_status(cls, value: object) -> str | None:
        text = _strip(value)
        if text is None:
            return None
        return _require_status(text)


@dataclass(slots=True)
class StampingDieUnitPriceInsert:
    location: str
    vehicle_model: str
    steel_plate_unit_price: Decimal
    progressive_die_unit_price: Decimal
    allocation_qty: Decimal
    status: str
    created_by: str
    updated_by: str


class StampingDieUnitPricePatch(TypedDict, total=False):
    location: str
    vehicle_model: str
    steel_plate_unit_price: Decimal
    progressive_die_unit_price: Decimal
    allocation_qty: Decimal
    status: str
    updated_by: str
