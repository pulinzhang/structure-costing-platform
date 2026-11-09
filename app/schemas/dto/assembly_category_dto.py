"""总成分类 DTO。"""

import re
from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator

_CODE = re.compile(r"^[a-z][a-z0-9_]*\Z")


def normalize_master_code(value: object) -> str:
    """去首尾空格并小写。只接受小写字母开头的编码。"""
    text = str(value or "").strip().lower()
    if not _CODE.fullmatch(text):
        raise ValueError("编码须以小写字母开头，只含小写字母、数字和下划线")
    return text


def strip_required_name(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("名称不能为空")
    return text


def strip_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class AssemblyCategoryQuery(BaseModel):
    """列表查询。"""

    q: str | None = Field(None, description="编码或名称")
    is_enabled: bool | None = Field(None, description="启用状态")
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)

    @field_validator("q", mode="before")
    @classmethod
    def strip_q(cls, value: object) -> str | None:
        return strip_optional_text(value)


class AssemblyCategoryCreate(BaseModel):
    """手建。编码创建后不改。"""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
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

    @field_validator("remark", mode="before")
    @classmethod
    def normalize_remark(cls, value: object) -> str | None:
        return strip_optional_text(value)


class AssemblyCategoryUpdate(BaseModel):
    """编辑名称、顺序、启用、备注。不含编码。"""

    name: str = Field(..., min_length=1, max_length=50)
    sort_order: int = Field(..., ge=0, le=9999)
    is_enabled: bool
    remark: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> str:
        return strip_required_name(value)

    @field_validator("remark", mode="before")
    @classmethod
    def normalize_remark(cls, value: object) -> str | None:
        return strip_optional_text(value)


@dataclass(slots=True)
class AssemblyCategoryInsert:
    """整行插入。"""

    code: str
    name: str
    sort_order: int
    is_enabled: bool
    remark: str | None
    created_by: str | None
    updated_by: str | None


@dataclass(slots=True)
class AssemblyCategoryPatch:
    """部分更新。不改编码。"""

    name: str
    sort_order: int
    is_enabled: bool
    remark: str | None
    updated_by: str | None
