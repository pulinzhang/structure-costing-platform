"""牌号分类档案 DTO。"""

from dataclasses import dataclass
from typing import TypedDict

from pydantic import BaseModel, Field, field_validator


def _strip(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


class SteelGradeCategoryQuery(BaseModel):
    """列表查询。"""

    grade: str | None = Field(None, description="牌号模糊")
    category_name: str | None = Field(None, description="大类精确：冷轧/镀锌/酸洗")
    uncategorized: bool = Field(False, description="只看待分类")
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)

    @field_validator("grade", "category_name", mode="before")
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip(value)


class SteelGradeCategoryExportQuery(BaseModel):
    """导出筛选（与列表一致，不分页）。"""

    grade: str | None = Field(None, description="牌号模糊")
    category_name: str | None = Field(None, description="大类精确：冷轧/镀锌/酸洗")
    uncategorized: bool = Field(False, description="只看待分类")

    @field_validator("grade", "category_name", mode="before")
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip(value)


class SteelGradeCategoryCreate(BaseModel):
    """手建。大类必填。"""

    grade: str = Field(..., min_length=1, max_length=50, description="钢材牌号")
    category_name: str = Field(..., min_length=1, max_length=50, description="大类")
    remark: str | None = Field(None, description="备注")

    @field_validator("grade", "category_name", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> str:
        text = _strip(value)
        if not text:
            raise ValueError("不能为空")
        return text

    @field_validator("remark", mode="before")
    @classmethod
    def strip_remark(cls, value: object) -> str | None:
        return _strip(value)


class SteelGradeCategoryUpdate(BaseModel):
    """编辑：可改大类与备注，不改牌号。"""

    category_name: str | None = Field(None, description="大类")
    remark: str | None = Field(None, description="备注")

    @field_validator("category_name", "remark", mode="before")
    @classmethod
    def strip_optional(cls, value: object) -> str | None:
        return _strip(value)


@dataclass(slots=True)
class GradeEnsureItem:
    """ensure_grades 入参一行。"""

    grade: str
    category_name: str | None = None


@dataclass(slots=True)
class SteelGradeCategoryInsert:
    """Repository 整行插入。"""

    grade: str
    category_name: str | None
    category_seq: int | None
    source: str
    remark: str | None
    created_by: str | None
    updated_by: str | None


class SteelGradeCategoryPatch(TypedDict, total=False):
    """部分更新。"""

    category_name: str | None
    category_seq: int | None
    remark: str | None
    updated_by: str


@dataclass(slots=True)
class GradeEnsureResult:
    """ensure_grades 结果（不穿过 HTTP）。"""

    inserted_count: int = 0
    claimed_count: int = 0
    skipped_count: int = 0
    conflicts: list[str] | None = None
