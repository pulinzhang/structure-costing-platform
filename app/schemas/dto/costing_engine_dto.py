"""核价引擎请求 DTO。"""

from pydantic import BaseModel, Field


class CostingEngineRunCreateDTO(BaseModel):
    """启动引擎 Run。"""

    location: str = Field(..., min_length=1, description="生产基地")
    year: int = Field(..., ge=2000, le=2100, description="核价年度")
    month: int = Field(..., ge=1, le=12, description="核价月份")
