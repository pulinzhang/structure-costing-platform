"""费用档案 DTO。"""

from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q6, quantize_money
from app.schemas.dto.assembly_category_dto import (
    normalize_master_code,
    strip_optional_text,
    strip_required_name,
)

_CHARGE_BASIS = frozenset({"amount", "rate"})


def normalize_charge_basis(value: object) -> str:
    text = str(value or "").strip().lower()
    if text not in _CHARGE_BASIS:
        raise ValueError("口径只能是金额或比例")
    return text


def normalize_charge_rate(value: object) -> Decimal:
    number = quantize_money(value, Q6)
    if number > Decimal("1"):
        raise ValueError("计费率不能超过 100%")
    return number


class FeeArchiveQuery(BaseModel):
    """列表查询。"""

    q: str | None = Field(None, description="编码或名称")
    is_enabled: bool | None = Field(None, description="启用状态")
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)

    @field_validator("q", mode="before")
    @classmethod
    def strip_q(cls, value: object) -> str | None:
        return strip_optional_text(value)


class FeeArchiveCreate(BaseModel):
    """手建。编码创建后不改。"""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    charge_basis: str = Field(..., min_length=1, max_length=20)
    charge_rate: Decimal
    sort_order: int = Field(..., ge=0, le=9999)
    remark: str | None = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> str:
        return normalize_master_code(value)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> str:
        return strip_required_name(value)

    @field_validator("charge_basis", mode="before")
    @classmethod
    def normalize_basis(cls, value: object) -> str:
        return normalize_charge_basis(value)

    @field_validator("charge_rate", mode="before")
    @classmethod
    def normalize_rate(cls, value: object) -> Decimal:
        return normalize_charge_rate(value)

    @field_validator("remark", mode="before")
    @classmethod
    def normalize_remark(cls, value: object) -> str | None:
        return strip_optional_text(value)


class FeeArchiveUpdate(BaseModel):
    """编辑名称、口径、计费率、顺序、启用、备注。不含编码。"""

    name: str = Field(..., min_length=1, max_length=50)
    charge_basis: str = Field(..., min_length=1, max_length=20)
    charge_rate: Decimal
    sort_order: int = Field(..., ge=0, le=9999)
    is_enabled: bool
    remark: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> str:
        return strip_required_name(value)

    @field_validator("charge_basis", mode="before")
    @classmethod
    def normalize_basis(cls, value: object) -> str:
        return normalize_charge_basis(value)

    @field_validator("charge_rate", mode="before")
    @classmethod
    def normalize_rate(cls, value: object) -> Decimal:
        return normalize_charge_rate(value)

    @field_validator("remark", mode="before")
    @classmethod
    def normalize_remark(cls, value: object) -> str | None:
        return strip_optional_text(value)


@dataclass(slots=True)
class FeeArchiveInsert:
    """整行插入。"""

    code: str
    name: str
    charge_basis: str
    charge_rate: Decimal
    sort_order: int
    is_enabled: bool
    remark: str | None
    created_by: str | None
    updated_by: str | None


@dataclass(slots=True)
class FeeArchivePatch:
    """部分更新。不改编码。"""

    name: str
    charge_basis: str
    charge_rate: Decimal
    sort_order: int
    is_enabled: bool
    remark: str | None
    updated_by: str | None
