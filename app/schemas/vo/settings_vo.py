"""
设置 VO - 响应数据结构
"""

from pydantic import BaseModel, Field, field_serializer


class ConfigVO(BaseModel):
    """系统配置 VO"""

    app_name: str
    version: str
    steel_density: float = Field(..., description="钢材密度(g/cm3)")
    material_loss_rate: float = Field(
        ..., description="冲压材料损耗率（小数，如 0.003=千分之3）"
    )
    scrap_recovery_rate: float = Field(
        ..., description="废料回收率（小数，如 0.97=97%）"
    )

    @field_serializer("steel_density", "material_loss_rate", "scrap_recovery_rate")
    def serialize_decimal_fields(self, value: float) -> float:
        return float(value)
