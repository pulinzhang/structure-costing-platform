"""系统设置 DTO - 请求参数"""

from pydantic import BaseModel, Field


class SystemConfigUpdateDTO(BaseModel):
    """更新系统配置"""

    app_name: str = Field(..., min_length=1, max_length=100, description="应用名称")
    steel_density: float = Field(
        ...,
        gt=0,
        le=20,
        description="钢材密度(g/cm3)",
    )
    material_loss_rate: float = Field(
        ...,
        ge=0,
        le=0.2,
        description="冲压材料损耗率（小数，如 0.003 表示千分之3）",
    )
    scrap_recovery_rate: float = Field(
        ...,
        gt=0,
        le=1,
        description="废料回收率（小数，如 0.97 表示 97%）",
    )
