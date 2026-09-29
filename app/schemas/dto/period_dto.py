"""生失效 PATCH 请求体（年+月，三块共用形状）。"""

from pydantic import BaseModel, Field

from app.common.period import (
    EFFECTIVE_YEAR_MAX,
    EFFECTIVE_YEAR_MIN,
    MONTH_MAX,
    MONTH_MIN,
)


class EffectivePeriodUpdateDTO(BaseModel):
    effective_year: int = Field(
        ..., ge=EFFECTIVE_YEAR_MIN, le=EFFECTIVE_YEAR_MAX, description="生效年"
    )
    effective_month: int = Field(..., ge=MONTH_MIN, le=MONTH_MAX, description="生效月")
    expiry_year: int | None = Field(
        None, ge=EFFECTIVE_YEAR_MIN, le=EFFECTIVE_YEAR_MAX, description="失效年；与失效月同空或同有"
    )
    expiry_month: int | None = Field(None, ge=MONTH_MIN, le=MONTH_MAX, description="失效月")
