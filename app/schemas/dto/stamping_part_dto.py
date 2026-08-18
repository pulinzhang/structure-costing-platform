"""
冲压零件 DTO - 请求参数
"""

from pydantic import BaseModel, Field


class StampingPartBatchDeleteDTO(BaseModel):
    """按基地 + 冲压工厂 + 车型 + 版本批量删除（四者同时必填）"""

    location: str = Field(..., min_length=1, description="采购基地（必填）")
    stamping_supplier: str = Field(..., min_length=1, description="冲压工厂（必填）")
    vehicle_model: str = Field(..., min_length=1, description="车型（必填）")
    version: str = Field(..., min_length=1, description="版本（必填）")
