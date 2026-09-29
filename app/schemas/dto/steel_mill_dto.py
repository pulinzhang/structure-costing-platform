"""钢厂档案 DTO。"""

from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator


def _mill_text(value: object) -> str:
    return str(value or "").strip().replace("（", "(").replace("）", ")")


def _names(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = _mill_text(value)
        return [text] if text else []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            text = _mill_text(item)
            if text:
                names.append(text)
        return names
    return []


class SteelMillQuery(BaseModel):
    """列表查询。"""

    q: str | None = Field(None, description="缩写 / 全称 / 别名")
    is_enabled: bool | None = Field(None, description="启用状态")
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)

    @field_validator("q", mode="before")
    @classmethod
    def strip_q(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class SteelMillCreate(BaseModel):
    """手建。"""

    abbreviation: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=50)
    remark: str | None = None
    aliases: list[str] = Field(default_factory=list)

    @field_validator("abbreviation", "full_name", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> str:
        text = _mill_text(value)
        if not text:
            raise ValueError("不能为空")
        return text

    @field_validator("remark", mode="before")
    @classmethod
    def strip_remark(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("aliases", mode="before")
    @classmethod
    def strip_aliases(cls, value: object) -> list[str]:
        return _names(value)


class SteelMillUpdate(BaseModel):
    """编辑缩写、全称、启用、备注、别名。"""

    abbreviation: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=50)
    is_enabled: bool
    remark: str | None = None
    aliases: list[str] = Field(default_factory=list)

    @field_validator("abbreviation", "full_name", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> str:
        text = _mill_text(value)
        if not text:
            raise ValueError("不能为空")
        return text

    @field_validator("remark", mode="before")
    @classmethod
    def strip_remark(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("aliases", mode="before")
    @classmethod
    def strip_aliases(cls, value: object) -> list[str]:
        return _names(value)


@dataclass(slots=True)
class SteelMillInsert:
    """整行插入。"""

    abbreviation: str
    full_name: str
    is_enabled: bool
    sort_order: int
    remark: str | None
    created_by: str | None
    updated_by: str | None


@dataclass(slots=True)
class SteelMillPatch:
    """部分更新。"""

    abbreviation: str
    full_name: str
    is_enabled: bool
    remark: str | None
    updated_by: str | None
