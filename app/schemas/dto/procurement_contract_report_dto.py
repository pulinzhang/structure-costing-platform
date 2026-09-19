"""采购价格查询入参。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProcurementContractReportQuery(BaseModel):
    location: str = Field(..., min_length=1, max_length=50)
    vehicle_model: str = Field(..., min_length=1, max_length=50)
    # 空 = 全部版本；列表可选浏览筛；导出必须空（Service 门禁）
    bom_version: str | None = Field(None, max_length=20)
    start_year: int = Field(..., ge=2000, le=2100)
    start_month: int = Field(..., ge=1, le=12)
    end_year: int = Field(..., ge=2000, le=2100)
    end_month: int = Field(..., ge=1, le=12)
    view: Literal["procurement", "assembly"] = "procurement"
    supplier_name: str | None = Field(None, max_length=100)
    keyword: str | None = Field(None, max_length=100, description="零件号或名称模糊（OR）")
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)

    @field_validator(
        "location",
        "vehicle_model",
        "bom_version",
        "supplier_name",
        "keyword",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None
