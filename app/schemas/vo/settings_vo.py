"""
设置 VO - 响应数据结构
"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from app.common.money import Q2, Q4, Q6, format_money


class ConfigVO(BaseModel):
    """系统配置 VO"""

    app_name: str
    company_name: str = Field(..., description="公司名称（采购协议甲方）")
    version: str
    steel_density: Decimal = Field(..., description="钢材密度(g/cm3)")
    material_loss_rate: Decimal = Field(..., description="冲压材料损耗率（小数，如 0.003=千分之3）")
    scrap_recovery_rate: Decimal = Field(..., description="废料回收率（小数，如 0.97=97%）")
    finished_finance_rate: Decimal = Field(..., description="成品财务费率（小数，如 0.02=2%）")
    finished_management_rate: Decimal = Field(..., description="成品管理费率（小数，如 0.02=2%）")
    finished_warehouse_packaging_rate: Decimal = Field(
        ..., description="仓储+包装管理费用率（小数，如 0.01=1%）"
    )
    finished_scrap_rate: Decimal = Field(..., description="成品报废率（小数，如 0.003=千分之3）")
    finished_pretax_profit_rate: Decimal = Field(
        ..., description="成品税前利润率（小数，如 0.02=2%）"
    )
    swing_shear_process_fee_per_ton: Decimal = Field(
        ..., description="摆剪件加到钢价上的金额（元/吨）"
    )

    @field_serializer("steel_density")
    def serialize_density(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)

    @field_serializer(
        "material_loss_rate",
        "scrap_recovery_rate",
        "finished_finance_rate",
        "finished_management_rate",
        "finished_warehouse_packaging_rate",
        "finished_scrap_rate",
        "finished_pretax_profit_rate",
    )
    def serialize_rate(self, value: Decimal) -> str:
        return format_money(value, Q6, 6)

    @field_serializer("swing_shear_process_fee_per_ton")
    def serialize_swing_shear_fee(self, value: Decimal) -> str:
        return format_money(value, Q2, 2)
