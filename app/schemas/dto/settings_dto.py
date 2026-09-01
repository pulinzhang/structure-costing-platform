"""系统设置 DTO - 请求参数 / Repository 写入载荷"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypedDict

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, Q6, quantize_money


class SystemConfigUpdateDTO(BaseModel):
    """更新系统配置"""

    app_name: str = Field(..., min_length=1, max_length=100, description="应用名称")
    steel_density: Decimal = Field(
        ...,
        gt=0,
        le=20,
        description="钢材密度(g/cm3)",
    )
    material_loss_rate: Decimal = Field(
        ...,
        ge=0,
        le=0.2,
        description="冲压材料损耗率（小数，如 0.003 表示千分之3）",
    )
    scrap_recovery_rate: Decimal = Field(
        ...,
        gt=0,
        le=1,
        description="废料回收率（小数，如 0.97 表示 97%）",
    )
    finished_finance_rate: Decimal = Field(
        ...,
        ge=0,
        le=1,
        description="成品财务费率（小数，如 0.02 表示 2%）",
    )
    finished_management_rate: Decimal = Field(
        ...,
        ge=0,
        le=1,
        description="成品管理费率（小数，如 0.02 表示 2%）",
    )
    finished_warehouse_packaging_rate: Decimal = Field(
        ...,
        ge=0,
        le=1,
        description="仓储+包装管理费用率（小数，如 0.01 表示 1%）",
    )
    finished_scrap_rate: Decimal = Field(
        ...,
        ge=0,
        le=0.2,
        description="成品报废率（小数，如 0.003 表示千分之3）",
    )
    finished_pretax_profit_rate: Decimal = Field(
        ...,
        ge=0,
        le=1,
        description="成品税前利润率（小数，如 0.02 表示 2%）",
    )

    @field_validator("steel_density", mode="before")
    @classmethod
    def _coerce_density(cls, value: Any) -> Decimal:
        return quantize_money(value, Q4)

    @field_validator(
        "material_loss_rate",
        "scrap_recovery_rate",
        "finished_finance_rate",
        "finished_management_rate",
        "finished_warehouse_packaging_rate",
        "finished_scrap_rate",
        "finished_pretax_profit_rate",
        mode="before",
    )
    @classmethod
    def _coerce_rate(cls, value: Any) -> Decimal:
        return quantize_money(value, Q6)


@dataclass(slots=True)
class SystemConfigWrite:
    """系统配置单例新建。"""

    app_name: str
    steel_density: Decimal
    material_loss_rate: Decimal
    scrap_recovery_rate: Decimal
    finished_finance_rate: Decimal
    finished_management_rate: Decimal
    finished_warehouse_packaging_rate: Decimal
    finished_scrap_rate: Decimal
    finished_pretax_profit_rate: Decimal
    created_by: str
    updated_by: str


class SystemConfigPatch(TypedDict, total=False):
    """系统配置部分更新。"""

    app_name: str
    steel_density: Decimal
    material_loss_rate: Decimal
    scrap_recovery_rate: Decimal
    finished_finance_rate: Decimal
    finished_management_rate: Decimal
    finished_warehouse_packaging_rate: Decimal
    finished_scrap_rate: Decimal
    finished_pretax_profit_rate: Decimal
    updated_by: str
