"""材料变更 DTO。"""

from pydantic import BaseModel, Field

from app.common.period import (
    MONTH_MAX,
    MONTH_MIN,
)


class MaterialChangeUploadQueryDTO(BaseModel):
    location: str | None = Field(None, description="采购基地")
    vehicle_model: str | None = Field(None, description="项目代号")
    change_version: str | None = Field(None, description="MAT-YYYYMM")
    effective_year: int | None = Field(None, ge=1, description="生效年")
    effective_month: int | None = Field(None, ge=MONTH_MIN, le=MONTH_MAX, description="生效月")
    status: str | None = Field(None, description="pending/success/failed")
    page: int = Field(1, ge=1, description="页码从 1")
    size: int = Field(20, ge=1, le=200, description="每页条数")
