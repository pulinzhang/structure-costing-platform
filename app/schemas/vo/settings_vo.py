"""
设置 VO - 响应数据结构
"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from app.common.money import Q4, Q6, format_money


class ConfigVO(BaseModel):
    """系统配置 VO"""

    app_name: str
    version: str
    steel_density: Decimal = Field(..., description="钢材密度(g/cm3)")
    material_loss_rate: Decimal = Field(
        ..., description="冲压材料损耗率（小数，如 0.003=千分之3）"
    )
    scrap_recovery_rate: Decimal = Field(
        ..., description="废料回收率（小数，如 0.97=97%）"
    )

    @field_serializer("steel_density")
    def serialize_density(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)

    @field_serializer("material_loss_rate", "scrap_recovery_rate")
    def serialize_rate(self, value: Decimal) -> str:
        return format_money(value, Q6, 6)
