"""工程变更 DTO — 入参。"""

from pydantic import BaseModel, Field

from app.common.period import (
    EFFECTIVE_YEAR_MAX,
    EFFECTIVE_YEAR_MIN,
    MONTH_MAX,
    MONTH_MIN,
)


class EngineeringChangeOrderQueryDTO(BaseModel):
    """工程变更单列表筛选。"""

    location: str | None = Field(None, description="采购基地")
    vehicle_model: str | None = Field(None, description="项目代号")
    effective_year: int | None = Field(
        None, ge=EFFECTIVE_YEAR_MIN, le=EFFECTIVE_YEAR_MAX, description="生效年"
    )
    effective_month: int | None = Field(None, ge=MONTH_MIN, le=MONTH_MAX, description="生效月")
    status: str | None = Field(None, description="pending/success/failed/rolled_back")
    change_type: str | None = Field(None, description="变更类型五句之一")
    page: int = Field(1, ge=1, description="页码从 1")
    size: int = Field(20, ge=1, le=200, description="每页条数")
