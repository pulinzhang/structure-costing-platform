"""生失效 PATCH 请求体（年+月，三块共用形状）。"""

from pydantic import BaseModel, Field


class EffectivePeriodUpdateDTO(BaseModel):
    effective_year: int = Field(..., ge=1990, le=2100, description="生效年")
    effective_month: int = Field(..., ge=1, le=12, description="生效月")
    expiry_year: int | None = Field(
        None, ge=1990, le=2100, description="失效年；与失效月同空或同有"
    )
    expiry_month: int | None = Field(None, ge=1, le=12, description="失效月")
