"""项目主数据 DTO。"""

from dataclasses import dataclass
from typing import TypedDict

from pydantic import BaseModel, Field, field_validator, model_validator


def _strip(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("格式不正确")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    raise ValueError("必须为整数")


class VehicleModelCreateDTO(BaseModel):
    """手工新增项目。"""

    location: str = Field(..., min_length=1, max_length=50, description="基地")
    vehicle_model: str = Field(..., min_length=1, max_length=50, description="项目代号")
    effective_year: int = Field(..., ge=1990, le=2100, description="生效年")
    effective_month: int = Field(..., ge=1, le=12, description="生效月")
    expiry_year: int | None = Field(None, ge=1990, le=2100, description="失效年")
    expiry_month: int | None = Field(None, ge=1, le=12, description="失效月")

    @field_validator("location", "vehicle_model", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> str:
        text = _strip(value)
        if not text:
            raise ValueError("不能为空")
        return text

    @field_validator("expiry_year", "expiry_month", mode="before")
    @classmethod
    def coerce_optional_int(cls, value: object) -> int | None:
        return _optional_int(value)

    @model_validator(mode="after")
    def expiry_pair(self) -> "VehicleModelCreateDTO":
        has_year = self.expiry_year is not None
        has_month = self.expiry_month is not None
        if has_year != has_month:
            raise ValueError("失效年与失效月必须同空或同有")
        if (
            has_year
            and has_month
            and (self.expiry_year, self.expiry_month) < (self.effective_year, self.effective_month)
        ):
            raise ValueError("失效不得早于生效")
        return self


class VehicleModelUpdateDTO(BaseModel):
    """改生效 / 失效。"""

    effective_year: int = Field(..., ge=1990, le=2100, description="生效年")
    effective_month: int = Field(..., ge=1, le=12, description="生效月")
    expiry_year: int | None = Field(None, ge=1990, le=2100, description="失效年")
    expiry_month: int | None = Field(None, ge=1, le=12, description="失效月")

    @field_validator("expiry_year", "expiry_month", mode="before")
    @classmethod
    def coerce_optional_int(cls, value: object) -> int | None:
        return _optional_int(value)

    @model_validator(mode="after")
    def expiry_pair(self) -> "VehicleModelUpdateDTO":
        has_year = self.expiry_year is not None
        has_month = self.expiry_month is not None
        if has_year != has_month:
            raise ValueError("失效年与失效月必须同空或同有")
        if (
            has_year
            and has_month
            and (self.expiry_year, self.expiry_month) < (self.effective_year, self.effective_month)
        ):
            raise ValueError("失效不得早于生效")
        return self


@dataclass(slots=True)
class VehicleModelInsert:
    """Repository 整行插入。"""

    location: str
    vehicle_model: str
    effective_year: int
    effective_month: int
    expiry_year: int | None
    expiry_month: int | None
    created_by: str | None
    updated_by: str | None


class VehicleModelPatch(TypedDict, total=False):
    """部分更新。"""

    effective_year: int
    effective_month: int
    expiry_year: int | None
    expiry_month: int | None
    updated_by: str
