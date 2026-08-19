"""
钢材基准价格 DTO - 内部传输数据结构
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional, TypedDict

from pydantic import BaseModel, Field, field_validator


def _strip(v: Optional[str]) -> Optional[str]:
    """去除首尾空白，无意义时返回 None"""
    if v is None:
        return None
    v = v.strip()
    return v if v else None


def _decimal_str(v: Optional[Decimal | float | int | str]) -> Optional[Decimal]:
    """将各种输入转为 Decimal，None 时返回 None"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


# ============================
# 创建 / 更新 DTO
# ============================

class SteelBasePriceCreate(BaseModel):
    """基准价格创建请求"""
    year: int = Field(..., ge=2000, le=2100, description="订单发布年份")
    month: int = Field(..., ge=1, le=12, description="订单发布月份")
    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    steel_mill: str = Field(..., min_length=1, max_length=50, description="中标钢厂")
    category_name: str = Field(..., min_length=1, max_length=50, description="钢种大类")
    grade: str = Field(..., min_length=1, max_length=50, description="钢材牌号")
    thick: Decimal = Field(..., ge=0, description="参考厚度(mm)")
    width: Decimal = Field(..., ge=0, description="参考宽度(mm)")
    base_price: Decimal = Field(..., ge=0, description="到厂原卷承兑价格(元/吨)")
    processing_fee: Decimal = Field(..., ge=0, description="原卷加工费(元/吨)")
    excel_filename: str = Field(..., min_length=1, max_length=255, description="来源Excel文件名")
    sheet_name: str = Field(..., min_length=1, max_length=100, description="Excel表页名称")
    excel_row: int = Field(..., ge=1, description="源数据在Excel中的行号")
    remark: Optional[str] = Field(None, description="备注")
    spec: Optional[str] = Field(None, max_length=50, description="规格，例：1.00*1250.00")

    @field_validator("location", "steel_mill", "category_name", "grade", "excel_filename", "sheet_name", "spec", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        return _strip(v)

    @field_validator("thick", "width", "base_price", "processing_fee", mode="before")
    @classmethod
    def coerce_decimals(cls, v: Any) -> Any:
        return _decimal_str(v)


class SteelBasePriceUpdate(BaseModel):
    """基准价格更新请求"""
    base_price: Optional[Decimal] = Field(None, ge=0, description="到厂原卷承兑价格(元/吨)")
    processing_fee: Optional[Decimal] = Field(None, ge=0, description="原卷加工费(元/吨)")
    excel_filename: Optional[str] = Field(None, max_length=255, description="来源Excel文件名")
    sheet_name: Optional[str] = Field(None, max_length=100, description="Excel表页名称")
    excel_row: Optional[int] = Field(None, ge=1, description="源数据在Excel中的行号")
    remark: Optional[str] = Field(None, description="备注")

    @field_validator("excel_filename", "sheet_name", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        return _strip(v)

    @field_validator("base_price", "processing_fee", mode="before")
    @classmethod
    def coerce_decimals(cls, v: Any) -> Any:
        return _decimal_str(v)


# ============================
# 查询 DTO
# ============================

class SteelBasePriceQuery(BaseModel):
    """基准价格分页筛选参数"""
    year: Optional[int] = Field(None, ge=2000, le=2100, description="订单发布年份")
    month: Optional[int] = Field(None, ge=1, le=12, description="订单发布月份")
    location: Optional[str] = Field(None, description="采购基地")
    steel_mill: Optional[str] = Field(None, description="中标钢厂")
    category_name: Optional[str] = Field(None, description="钢种大类")
    grade: Optional[str] = Field(None, description="钢材牌号")
    spec: Optional[str] = Field(None, description="规格")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=200, description="每页条数")

    @field_validator("location", "steel_mill", "category_name", "grade", "spec", mode="before")
    @classmethod
    def strip_query_strings(cls, v: Any) -> Any:
        return _strip(v)


# ============================
# 筛选选项 DTO
# ============================

class FilterOptions(BaseModel):
    """筛选选项 DTO（Repository → Service 层内部使用）"""

    years: list[int] = Field(default_factory=list)
    months: list[int] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    steel_mills: list[str] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)
    grades: list[str] = Field(default_factory=list)
    specs: list[str] = Field(default_factory=list)


# ============================
# Repository 写入载荷
# ============================

@dataclass(slots=True)
class SteelBasePriceWrite:
    """基准价格导入 / upsert 整行写入（含溯源列与审计人）。"""

    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thick: Decimal | None
    width: Decimal | None
    base_price: Decimal
    processing_fee: Decimal
    excel_filename: str
    sheet_name: str
    excel_row: int
    spec: str | None = None
    excel_col: int | None = None
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


class BasePriceUpsertCounts(TypedDict):
    """upsert 返回的新增 / 更新条数。"""

    created: int
    updated: int
