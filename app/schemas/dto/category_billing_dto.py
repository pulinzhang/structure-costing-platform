"""计费管理 DTO。"""

from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator


class AssemblyCategoryBillingQuery(BaseModel):
    """列表查询。"""

    assembly_category_id: int | None = Field(None, ge=1, description="按总成分类筛选")
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)


class CategoryBillingReplace(BaseModel):
    """一次写入某个分类勾选的费用。空列表表示这个分类不计费。"""

    fee_archive_ids: list[int] = Field(default_factory=list, max_length=100)

    @field_validator("fee_archive_ids")
    @classmethod
    def unique_fee_ids(cls, value: list[int]) -> list[int]:
        if any(item < 1 for item in value):
            raise ValueError("费用编号无效")
        if len(set(value)) != len(value):
            raise ValueError("同一费用不能重复勾选")
        return value


@dataclass(slots=True)
class AssemblyCategoryBillingInsert:
    """整行插入。顺序读费用档案，不另存。"""

    assembly_category_id: int
    fee_archive_id: int
    remark: str | None
    created_by: str | None
    updated_by: str | None
