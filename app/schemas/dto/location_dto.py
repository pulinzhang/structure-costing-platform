"""基地主数据 DTO。"""

from dataclasses import dataclass
from typing import TypedDict

from pydantic import BaseModel, Field, field_validator


def _strip(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


class LocationCreateDTO(BaseModel):
    """新增基地。规范名与别名一次录入；别名至少一条，可多条；默认已启用。"""

    location: str = Field(..., min_length=1, max_length=50, description="规范名")
    aliases: list[str] = Field(..., min_length=1, description="别名，至少一条")

    @field_validator("location", mode="before")
    @classmethod
    def strip_location(cls, value: object) -> str:
        text = _strip(value)
        if not text:
            raise ValueError("不能为空")
        return text

    @field_validator("aliases", mode="before")
    @classmethod
    def coerce_aliases(cls, value: object) -> list[object]:
        if isinstance(value, list):
            return value
        raise ValueError("别名格式不正确")

    @field_validator("aliases")
    @classmethod
    def strip_aliases(cls, value: list[object]) -> list[str]:
        result: list[str] = []
        for item in value:
            text = _strip(item)
            if not text:
                continue
            if len(text) > 50:
                raise ValueError("别名最长 50 字")
            if text not in result:
                result.append(text)
        if not result:
            raise ValueError("不能为空")
        return result


class LocationUpdateDTO(BaseModel):
    """启用 / 禁用。"""

    is_enabled: bool = Field(..., description="是否启用")


class LocationAliasCreateDTO(BaseModel):
    """新增别名。"""

    alias: str = Field(..., min_length=1, max_length=50, description="别名")

    @field_validator("alias", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> str:
        text = _strip(value)
        if not text:
            raise ValueError("不能为空")
        return text


@dataclass(slots=True)
class LocationInsert:
    """Repository 整行插入。"""

    location: str
    is_enabled: bool
    sort_order: int
    created_by: str | None
    updated_by: str | None


class LocationPatch(TypedDict, total=False):
    """部分更新。"""

    is_enabled: bool
    updated_by: str


@dataclass(slots=True)
class LocationAliasInsert:
    """别名插入。"""

    alias: str
    location: str
