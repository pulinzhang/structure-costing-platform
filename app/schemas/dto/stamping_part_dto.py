"""
冲压零件 DTO - 请求参数
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q2, quantize_money
from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
    MONTH_MAX,
    MONTH_MIN,
)


class StampingPartOffalUpdateDTO(BaseModel):
    """零件详情：是否利废 / 利用哪类废料"""

    is_offal_nested: bool = Field(..., description="是否利废")
    offal_source: str | None = Field(None, max_length=50, description="利用哪类废料")

    @field_validator("offal_source", mode="before")
    @classmethod
    def _strip_offal_source(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class StampingPartBatchDeleteDTO(BaseModel):
    """按基地 + 车型 + 版本批量删除；冲压工厂可选（空则覆盖该车各厂）"""

    location: str = Field(..., min_length=1, description="采购基地（必填）")
    vehicle_model: str = Field(..., min_length=1, description="车型（必填）")
    version: str = Field(..., min_length=1, description="版本（必填）")
    stamping_supplier: str | None = Field(None, description="冲压工厂（可选）")

    @field_validator("stamping_supplier", mode="before")
    @classmethod
    def _empty_supplier_to_none(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class StampingPartQuery(BaseModel):
    """冲压零件查询参数"""

    location: str | None = Field(None, description="采购基地")
    vehicle_model: str | None = Field(None, description="项目")
    version: str | None = Field(None, description="版本")
    part_number: str | None = Field(None, description="零件号")
    part_name: str | None = Field(None, description="零件名称")
    material: str | None = Field(None, description="材质")
    stamping_supplier: str | None = Field(None, description="冲压供应商")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")
    year: int | None = Field(
        None, ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="查看年；空则墙钟"
    )
    month: int | None = Field(
        None, ge=MONTH_MIN, le=MONTH_MAX, description="查看月；与年同空或同有"
    )
    include_expired: bool = Field(False, description="含已失效；零件列表不提供开关")


class StampingProcessUpdate(BaseModel):
    """工序更新请求"""

    cost_ratio: Decimal | None = Field(
        None, ge=0, le=10, description="成本系数（0~10，即0%~1000%）"
    )
    remark: str | None = None

    @field_validator("cost_ratio", mode="before")
    @classmethod
    def _coerce_cost_ratio(cls, value: Any) -> Decimal | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return quantize_money(value, Q2)


class StampingProcessItemUpdate(BaseModel):
    """单个工序更新项"""

    id: int
    cost_ratio: Decimal | None = Field(
        None, ge=0, le=10, description="成本系数（0~10，即0%~1000%）"
    )
    remark: str | None = None

    @field_validator("cost_ratio", mode="before")
    @classmethod
    def _coerce_cost_ratio(cls, value: Any) -> Decimal | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return quantize_money(value, Q2)


class StampingCascadeFilterQuery(BaseModel):
    """冲压级联筛选查询参数"""

    location: str | None = Field(None, description="采购基地")
    stamping_supplier: str | None = Field(None, description="冲压工厂")
    vehicle_model: str | None = Field(None, description="项目")
    version: str | None = Field(None, description="版本")
    year: int | None = Field(
        None,
        ge=COSTING_YEAR_MIN,
        le=COSTING_YEAR_MAX,
        description="年度；只带年时项目下拉按冲压件有效期年交集",
    )
    month: int | None = Field(
        None, ge=MONTH_MIN, le=MONTH_MAX, description="月份；与年度一起时下拉为该月可引入"
    )


class StampingMaterialQuery(BaseModel):
    """材料查询参数"""

    location: str | None = Field(None, description="采购基地")
    stamping_supplier: str | None = Field(None, description="冲压供应商")
    vehicle_model: str | None = Field(None, description="项目")
    version: str | None = Field(None, description="版本")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(50, ge=1, le=500, description="每页条数")
