"""
拼焊子片 DTO - 请求参数

子片材料侧录入；工序仍挂父件。blank_part_number / parent_part_number
一般由 Service 按父零件号自动填写，DTO 可不传。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypedDict

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common.money import Q2, Q4, optional_quantize_money


def _strip(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return value


class StampingTailorWeldBlankItemDTO(BaseModel):
    """单片子片录入项（用于新增或整组替换）。"""

    blank_seq: int | None = Field(
        default=None,
        ge=1,
        description="子片序号，从 1 起；整组替换时可省略，按列表顺序自动 1..N",
    )
    blank_part_number: str | None = Field(
        default=None,
        max_length=60,
        description="子件零件号；省略则自动生成「父零件号-序号」",
    )
    material: str | None = Field(default=None, max_length=50, description="材质")
    thickness: Decimal | None = Field(default=None, description="料厚(mm)")
    part_weight: Decimal | None = Field(default=None, description="子片重量(kg)")
    sheet_length: Decimal | None = Field(default=None, description="料片长/卷料宽(mm)")
    sheet_width: Decimal | None = Field(default=None, description="料片宽/卷料步距(mm)")
    parts_per_sheet: int | None = Field(default=None, ge=1, description="可制件数")
    sheet_type: str | None = Field(default=None, max_length=50, description="料片式样")
    remark: str | None = Field(default=None, description="备注")

    @field_validator(
        "blank_part_number",
        "material",
        "sheet_type",
        "remark",
        mode="before",
    )
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_strings(cls, value: object) -> Any:
        return _strip(value)

    @field_validator("thickness", "part_weight", mode="before")
    @classmethod
    def coerce_physical(cls, value: object) -> Decimal | None:
        return optional_quantize_money(value, Q4)

    @field_validator("sheet_length", "sheet_width", mode="before")
    @classmethod
    def coerce_sheet_dim(cls, value: object) -> Decimal | None:
        return optional_quantize_money(value, Q2)


class StampingTailorWeldBlankCreateDTO(StampingTailorWeldBlankItemDTO):
    """新增单片子片；blank_seq 必填。"""

    blank_seq: int = Field(..., ge=1, description="子片序号，从 1 起")


class StampingTailorWeldBlankUpdateDTO(BaseModel):
    """更新单片子片（部分字段）。"""

    blank_seq: int | None = Field(default=None, ge=1, description="子片序号")
    blank_part_number: str | None = Field(default=None, max_length=60, description="子件零件号")
    material: str | None = Field(default=None, max_length=50)
    thickness: Decimal | None = None
    part_weight: Decimal | None = None
    sheet_length: Decimal | None = None
    sheet_width: Decimal | None = None
    parts_per_sheet: int | None = Field(default=None, ge=1)
    sheet_type: str | None = Field(default=None, max_length=50)
    remark: str | None = None

    @field_validator(
        "blank_part_number",
        "material",
        "sheet_type",
        "remark",
        mode="before",
    )
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_strings(cls, value: object) -> Any:
        return _strip(value)

    @field_validator("thickness", "part_weight", mode="before")
    @classmethod
    def coerce_physical(cls, value: object) -> Decimal | None:
        return optional_quantize_money(value, Q4)

    @field_validator("sheet_length", "sheet_width", mode="before")
    @classmethod
    def coerce_sheet_dim(cls, value: object) -> Decimal | None:
        return optional_quantize_money(value, Q2)


class StampingTailorWeldBlankReplaceDTO(BaseModel):
    """按父件整组替换子片（至少两片）。"""

    items: list[StampingTailorWeldBlankItemDTO] = Field(
        ...,
        min_length=2,
        description="子片列表，至少 2 片",
    )

    @model_validator(mode="after")
    def validate_unique_seq(self) -> StampingTailorWeldBlankReplaceDTO:
        seqs = [item.blank_seq for item in self.items if item.blank_seq is not None]
        if len(seqs) != len(set(seqs)):
            raise ValueError("blank_seq 不能重复")
        numbers = [
            item.blank_part_number for item in self.items if item.blank_part_number is not None
        ]
        if len(numbers) != len(set(numbers)):
            raise ValueError("blank_part_number 不能重复")
        return self


@dataclass(slots=True)
class TailorWeldBlankWrite:
    """拼焊子片新建（含父件与审计人）。"""

    part_id: int
    parent_part_number: str
    blank_seq: int
    blank_part_number: str
    material: str | None = None
    thickness: Decimal | None = None
    part_weight: Decimal | None = None
    sheet_length: Decimal | None = None
    sheet_width: Decimal | None = None
    parts_per_sheet: int | None = None
    sheet_type: str | None = None
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


class TailorWeldBlankPatch(TypedDict, total=False):
    """拼焊子片部分更新。"""

    blank_seq: int
    blank_part_number: str
    material: str | None
    thickness: Decimal | None
    part_weight: Decimal | None
    sheet_length: Decimal | None
    sheet_width: Decimal | None
    parts_per_sheet: int | None
    sheet_type: str | None
    remark: str | None
    parent_part_number: str
    updated_by: str
