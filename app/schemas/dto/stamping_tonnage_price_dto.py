"""
冲次单价 DTO - 内部传输/请求参数
"""

from pydantic import BaseModel, Field


class StampingTonnagePriceCreate(BaseModel):
    """冲次单价创建请求"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    year: int = Field(..., ge=2000, le=2100, description="年份")
    tonnage: int = Field(..., ge=1, description="压机吨位(T)")
    price_per_stroke: float = Field(..., ge=0, description="单冲次价格(元)")


class StampingTonnagePriceUpdate(BaseModel):
    """冲次单价更新请求"""

    price_per_stroke: float = Field(..., ge=0, description="单冲次价格(元)")


class StampingTonnagePriceQuery(BaseModel):
    """冲次单价查询参数"""

    location: str | None = Field(None, description="采购基地")
    year: int | None = Field(None, description="年份")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")


class StampingTonnagePriceBatchDeleteDTO(BaseModel):
    """按基地 + 年度批量删除"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地（必填）")
    year: int = Field(..., ge=2000, le=2100, description="年度（必填）")
