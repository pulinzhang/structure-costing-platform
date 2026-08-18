"""
冲压废料月度销售价格 DTO - 请求参数（以「月」为录入单元）
"""

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common.money import Q2, optional_quantize_money, quantize_money
from app.common.scrap_price_locations import (
    SCRAP_PRICE_LOCATION_COUNT,
    SCRAP_PRICE_LOCATIONS,
)


def _strip(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value if value else None


class StampingScrapPriceMonthRowInput(BaseModel):
    """月度矩阵中单行（基地）录入项"""

    location: str = Field(..., min_length=1, max_length=50, description="基地/物料名称")
    market_price: Decimal = Field(..., ge=0, description="大盘价（元/吨）")
    deduction_fee: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="扣费（元/吨）",
    )
    remark: Optional[str] = Field(None, description="备注")

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
    """整月一次提交：必须覆盖全部固定基地，不多不少"""

    year: int = Field(..., ge=2000, le=2100, description="年份")
    month: int = Field(..., ge=1, le=12, description="月份（1-12）")
    items: list[StampingScrapPriceMonthRowInput] = Field(
        ...,
        min_length=SCRAP_PRICE_LOCATION_COUNT,
        max_length=SCRAP_PRICE_LOCATION_COUNT,
        description="固定 6 个基地的价格行",
    )

    @model_validator(mode="after")
    def validate_fixed_locations(self) -> Any:
        expected = list(SCRAP_PRICE_LOCATIONS)
        actual = [row.location for row in self.items]
        if sorted(actual) != sorted(expected):
            raise ValueError(
                f"items 必须恰好包含且仅包含固定基地: {', '.join(expected)}"
            )
        if len(set(actual)) != len(actual):
            raise ValueError("items 中基地名称不能重复")
        # 按固定顺序重排，便于落库与前端展示一致
        by_location = {row.location: row for row in self.items}
        self.items = [by_location[name] for name in expected]
        return self


class StampingScrapPriceCopyMonth(BaseModel):
    """从源年月复制到目标年月"""

    source_year: int = Field(..., ge=2000, le=2100, description="源年份")
    source_month: int = Field(..., ge=1, le=12, description="源月份")
    target_year: int = Field(..., ge=2000, le=2100, description="目标年份")
    target_month: int = Field(..., ge=1, le=12, description="目标月份")


class FilterOptions(BaseModel):
    """筛选选项（Repository → Service 内部）"""

    years: list[int] = Field(default_factory=list)
