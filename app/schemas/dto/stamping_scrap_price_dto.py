"""
冲压废料月度销售价格 DTO - 请求参数（以「月 + 类别」为录入单元）
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common.money import Q2, optional_quantize_money, quantize_money
from app.common.scrap_categories import SCRAP_CATEGORY_STEEL, ScrapCategory


def _strip(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value if value else None


class StampingScrapPriceMonthRowInput(BaseModel):
    """月度矩阵中单行（基地）录入项"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    market_price: Decimal = Field(..., ge=0, description="大盘价（元/吨）")
    deduction_fee: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="扣费（元/吨）",
    )
    remark: str | None = Field(None, description="备注")

    @field_validator("location", "remark", mode="before")
    @classmethod
    def strip_strings(cls, value: Any) -> Any:
        return _strip(value)

    @field_validator("market_price", mode="before")
    @classmethod
    def coerce_market_price(cls, value: Any) -> Decimal:
        return quantize_money(value, Q2)

    @field_validator("deduction_fee", mode="before")
    @classmethod
    def coerce_deduction_fee(cls, value: Any) -> Decimal:
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return Decimal("0.00")
        return optional_quantize_money(value, Q2) or Decimal("0.00")

    @model_validator(mode="after")
    def validate_deduction_not_exceed_market(self) -> Any:
        if self.deduction_fee > self.market_price:
            raise ValueError(f"{self.location}: 扣费不能大于大盘价")
        return self


class StampingScrapPriceMonthSaveDTO(BaseModel):
    """整月一次提交：覆盖当前类别下全部已启用基地。"""

    year: int = Field(..., ge=2000, le=2100, description="年份")
    month: int = Field(..., ge=1, le=12, description="月份（1-12）")
    scrap_category: ScrapCategory = Field(
        default=SCRAP_CATEGORY_STEEL,
        description="废料类别：钢材 / 铝板",
    )
    items: list[StampingScrapPriceMonthRowInput] = Field(
        ...,
        min_length=1,
        description="已启用基地价格行",
    )

    @model_validator(mode="after")
    def validate_unique_locations(self) -> Any:
        names = [row.location for row in self.items]
        if len(set(names)) != len(names):
            raise ValueError("items 中基地名称不能重复")
        return self


class StampingScrapPriceCopyMonth(BaseModel):
    """从源年月复制到目标年月（仅当前类别）"""

    source_year: int = Field(..., ge=2000, le=2100, description="源年份")
    source_month: int = Field(..., ge=1, le=12, description="源月份")
    target_year: int = Field(..., ge=2000, le=2100, description="目标年份")
    target_month: int = Field(..., ge=1, le=12, description="目标月份")
    scrap_category: ScrapCategory = Field(
        default=SCRAP_CATEGORY_STEEL,
        description="废料类别：钢材 / 铝板",
    )


@dataclass(slots=True)
class ScrapPriceWrite:
    """废料月度销售价整行写入（含净价与审计人）。"""

    year: int
    month: int
    location: str
    scrap_category: str
    market_price: Decimal
    deduction_fee: Decimal
    net_price: Decimal
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
