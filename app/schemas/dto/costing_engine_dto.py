"""核价引擎请求 DTO。"""

from pydantic import BaseModel, Field

from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
    MONTH_MAX,
    MONTH_MIN,
)


class CostingEngineRunCreateDTO(BaseModel):
    """启动引擎 Run。"""

    location: str = Field(..., min_length=1, description="生产基地")
    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="核价年度")
    month: int = Field(..., ge=MONTH_MIN, le=MONTH_MAX, description="核价月份")
