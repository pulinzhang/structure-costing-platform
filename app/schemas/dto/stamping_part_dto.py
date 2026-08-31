"""
冲压零件 DTO - 请求参数
"""

from pydantic import BaseModel, Field, field_validator


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
    """按基地 + 冲压工厂 + 车型 + 版本批量删除（四者同时必填）"""

    location: str = Field(..., min_length=1, description="采购基地（必填）")
    stamping_supplier: str = Field(..., min_length=1, description="冲压工厂（必填）")
    vehicle_model: str = Field(..., min_length=1, description="车型（必填）")
    version: str = Field(..., min_length=1, description="版本（必填）")
