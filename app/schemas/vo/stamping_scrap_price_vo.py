"""
冲压废料月度销售价格 VO - 响应数据结构（以「月」为维护单元）
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from app.common.money import Q2, optional_format_money
from app.common.scrap_price_locations import SCRAP_PRICE_LOCATIONS


class StampingScrapPriceMonthRowVO(BaseModel):
    """月度矩阵单行；未录入时价格字段为 null"""

    location: str
    id: int | None = None
    market_price: Decimal | None = None
    deduction_fee: Decimal | None = None
    net_price: Decimal | None = None
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("market_price", "deduction_fee", "net_price")
    def serialize_price(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class StampingScrapPriceMonthSheetVO(BaseModel):
    """整月录入/维护表单：固定 6 行，顺序与 SCRAP_PRICE_LOCATIONS 一致"""

    year: int
    month: int
    is_saved: bool = Field(..., description="该月是否已有任意记录")
    is_complete: bool = Field(..., description="是否已录满全部固定基地")
    filled_count: int = Field(..., description="已录入行数")
    locations: list[str] = Field(
        default_factory=lambda: list(SCRAP_PRICE_LOCATIONS),
        description="固定基地顺序",
    )
    items: list[StampingScrapPriceMonthRowVO]


class StampingScrapPriceMonthSummaryVO(BaseModel):
    """已维护月份列表项（维护页导航）"""

    year: int
    month: int
    filled_count: int
    is_complete: bool
    updated_at: datetime | None = None

    @field_serializer("updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class StampingScrapPriceFilterOptionsVO(BaseModel):
    """筛选下拉：已有数据的年份 + 固定基地清单"""

    years: list[int] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=lambda: list(SCRAP_PRICE_LOCATIONS))


class StampingScrapPriceCopyMonthResponse(BaseModel):
    """跨月复制结果"""

    source_year: int
    source_month: int
    target_year: int
    target_month: int
    created_count: int
