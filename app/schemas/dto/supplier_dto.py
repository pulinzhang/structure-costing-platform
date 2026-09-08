"""供应商主数据 DTO。"""

from dataclasses import dataclass
from typing import TypedDict

from pydantic import BaseModel, Field, field_validator


def _strip(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


class SupplierQuery(BaseModel):
    """一览表分页查询。"""

    q: str | None = Field(None, description="关键字：缩写 / 全称 / ERP / 别名")
    is_enabled: bool | None = Field(None, description="启用状态；不传则全部")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(10, ge=1, le=100, description="每页条数")

    @field_validator("q", mode="before")
    @classmethod
    def strip_keyword(cls, value: object) -> str | None:
        return _strip(value)


class SupplierCreateDTO(BaseModel):
    """手工新增。缩写、全称、ERP 必填；别名可空。默认已启用。"""

    abbreviation: str = Field(..., min_length=1, max_length=50, description="缩写")
    full_name: str = Field(..., min_length=1, max_length=100, description="全称")
    erp_code: str = Field(..., min_length=1, max_length=50, description="ERP 代码")
    aliases: list[str] = Field(default_factory=list, description="别名，可空")

    @field_validator("abbreviation", "full_name", "erp_code", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> str:
        text = _strip(value)
        if not text:
            raise ValueError("不能为空")
        return text

    @field_validator("aliases", mode="before")
    @classmethod
    def coerce_aliases(cls, value: object) -> list[object]:
        if value is None:
            return []
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
            if len(text) > 100:
                raise ValueError("别名最长 100 字")
            if text not in result:
                result.append(text)
        return result


class SupplierUpdateDTO(BaseModel):
    """启用 / 禁用，以及改缩写、全称、ERP。未传的字段不改。"""

    abbreviation: str | None = Field(None, min_length=1, max_length=50, description="缩写")
    full_name: str | None = Field(None, min_length=1, max_length=100, description="全称")
    erp_code: str | None = Field(None, min_length=1, max_length=50, description="ERP 代码")
    is_enabled: bool | None = Field(None, description="是否启用")

    @field_validator("abbreviation", "full_name", "erp_code", mode="before")
    @classmethod
    def strip_optional_identity(cls, value: object) -> str | None:
        if value is None:
            return None
        text = _strip(value)
        if not text:
            raise ValueError("不能为空")
        return text


class SupplierAliasCreateDTO(BaseModel):
    """新增别名。"""

    alias: str = Field(..., min_length=1, max_length=100, description="别名")

    @field_validator("alias", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> str:
        text = _strip(value)
        if not text:
            raise ValueError("不能为空")
        return text


@dataclass(slots=True)
class SupplierInsert:
    """Repository 整行插入。"""

    full_name: str
    abbreviation: str
    erp_code: str
    is_enabled: bool
    sort_order: int
    created_by: str | None
    updated_by: str | None


class SupplierPatch(TypedDict, total=False):
    """部分更新。"""

    abbreviation: str
    erp_code: str
    is_enabled: bool
    updated_by: str


@dataclass(slots=True)
class SupplierAliasInsert:
    """别名插入。"""

    alias: str
    full_name: str
