"""
焊接工费单价 DTO - 内部传输/请求参数
"""

from pydantic import BaseModel, Field


class BomWeldingUnitPriceCreate(BaseModel):
    """焊接工费单价创建请求"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    year: int = Field(..., ge=2000, le=2100, description="年份")
    item_name: str = Field(..., min_length=1, max_length=100, description="操作项目名称")
    unit: str = Field(..., min_length=1, max_length=20, description="计量单位")
    unit_price: float = Field(..., ge=0, description="工费单价(元/单位)")
    remark: str | None = Field(None, description="备注")


class BomWeldingUnitPriceUpdate(BaseModel):
    """焊接工费单价更新请求"""

    unit: str | None = Field(None, min_length=1, max_length=20, description="计量单位")
    unit_price: float = Field(..., ge=0, description="工费单价(元/单位)")
    remark: str | None = Field(None, description="备注")


class BomWeldingUnitPriceQuery(BaseModel):
    """焊接工费单价查询参数"""

    location: str | None = Field(None, description="采购基地")
    year: int | None = Field(None, description="年份")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")


class BomWeldingUnitPriceBatchDeleteDTO(BaseModel):
    """按基地 + 年度批量删除"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地（必填）")
    year: int = Field(..., ge=2000, le=2100, description="年度（必填）")
