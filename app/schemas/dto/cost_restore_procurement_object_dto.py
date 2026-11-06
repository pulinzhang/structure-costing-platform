"""成本还原 — 采购对象查询入参。"""

from pydantic import BaseModel, Field, field_validator

from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
    MONTH_MAX,
    MONTH_MIN,
)


class CostRestoreProcurementObjectQuery(BaseModel):
    location: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX)
    month: int = Field(..., ge=MONTH_MIN, le=MONTH_MAX)
    vehicle_model: str | None = Field(None, max_length=50)
    supplier_name: str | None = Field(None, max_length=100)
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)

    @field_validator("location", "vehicle_model", "supplier_name", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        return value
