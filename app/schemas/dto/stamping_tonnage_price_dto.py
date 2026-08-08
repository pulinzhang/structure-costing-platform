"""
吨位价格 DTO - 内部传输/请求参数
"""

from typing import List

from pydantic import BaseModel, Field


class StampingTonnagePriceCreate(BaseModel):
    """吨位价格创建请求"""

    year: int = Field(..., ge=2000, le=2100, description="年份")
    tonnage: int = Field(..., ge=1, description="压机吨位(T)")
    price_per_stroke: float = Field(..., ge=0, description="单冲次价格(元)")


class StampingTonnagePriceUpdate(BaseModel):
    """吨位价格更新请求"""

    price_per_stroke: float = Field(..., ge=0, description="单冲次价格(元)")


class StampingTonnagePriceQuery(BaseModel):
    """吨位价格查询参数"""

    year: int | None = Field(None, description="年份")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")


class StampingTonnagePriceBulkCreate(BaseModel):
    """吨位价格批量创建请求"""

    items: List[StampingTonnagePriceCreate] = Field(..., min_length=1, description="批量创建项")


class StampingTonnagePriceCopyTemplate(BaseModel):
    """从指定年份复制价格模板"""

    source_year: int = Field(..., ge=2000, le=2100, description="源年份")
    target_year: int = Field(..., ge=2000, le=2100, description="目标年份")
