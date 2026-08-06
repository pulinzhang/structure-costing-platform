"""
钢材基准价格请求与响应 DTO
全程使用 Decimal 表示尺寸和金额，绝不转换为 float
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator


def _strip(v: Optional[str]) -> Optional[str]:
    """去除首尾空白，无意义时返回 None"""
    if v is None:
        return None
    v = v.strip()
    return v if v else None


def _decimal_str(v: Any) -> Optional[Decimal]:
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
    thick: Decimal = Field(..., ge=Decimal("0"), description="参考厚度(mm)")
    width: Decimal = Field(..., ge=Decimal("0"), description="参考宽度(mm)")
    base_price: Decimal = Field(..., ge=Decimal("0"), description="到厂原卷承兑价格(元/吨)")
    processing_fee: Decimal = Field(..., ge=Decimal("0"), description="原卷加工费(元/吨)")
    excel_filename: str = Field(..., min_length=1, max_length=255, description="来源Excel文件名")
    sheet_name: str = Field(..., min_length=1, max_length=100, description="Excel表页名称")
    excel_row: int = Field(..., ge=1, description="源数据在Excel中的行号")
    remark: Optional[str] = Field(None, description="备注")

    @field_validator("location", "steel_mill", "category_name", "grade", "excel_filename", "sheet_name", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return _strip(v)

    @field_validator("thick", "width", "base_price", "processing_fee", mode="before")
    @classmethod
    def coerce_decimals(cls, v):
        return _decimal_str(v)


class SteelBasePriceUpdate(BaseModel):
    """基准价格更新请求（业务键 year/month/location/steel_mill/category_name/grade/thick/width 不允许变更）"""
    base_price: Optional[Decimal] = Field(None, ge=Decimal("0"), description="到厂原卷承兑价格(元/吨)")
    processing_fee: Optional[Decimal] = Field(None, ge=Decimal("0"), description="原卷加工费(元/吨)")
    excel_filename: Optional[str] = Field(None, max_length=255, description="来源Excel文件名")
    sheet_name: Optional[str] = Field(None, max_length=100, description="Excel表页名称")
    excel_row: Optional[int] = Field(None, ge=1, description="源数据在Excel中的行号")
    remark: Optional[str] = Field(None, description="备注")

    @field_validator("excel_filename", "sheet_name", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return _strip(v)

    @field_validator("base_price", "processing_fee", mode="before")
    @classmethod
    def coerce_decimals(cls, v):
        return _decimal_str(v)

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        """至少需要提供一个可更新字段"""
        if all(
            v is None
            for v in (
                self.base_price,
                self.processing_fee,
                self.excel_filename,
                self.sheet_name,
                self.excel_row,
                self.remark,
            )
        ):
            raise ValueError("至少需要提供一个可更新字段")
        return self


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
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=200, description="每页条数")

    @field_validator("location", "steel_mill", "category_name", "grade", mode="before")
    @classmethod
    def strip_query_strings(cls, v):
        return _strip(v)


# ============================
# 响应 DTO
# ============================

class SteelBasePriceResponse(BaseModel):
    """基准价格响应"""
    id: int
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thick: Decimal
    width: Decimal
    base_price: Decimal
    processing_fee: Decimal
    excel_filename: str
    sheet_name: str
    excel_row: int
    excel_col: Optional[int] = None
    remark: Optional[str]
    created_at: datetime
    updated_at: datetime

    @field_serializer("thick", "width", "base_price", "processing_fee")
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    model_config = {"from_attributes": True}


class SteelBasePriceOptionsResponse(BaseModel):
    """基准价格筛选下拉选项"""
    years: list[int] = Field(default_factory=list)
    months: list[int] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    steel_mills: list[str] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)
    grades: list[str] = Field(default_factory=list)


class SteelBasePriceImportResultResponse(BaseModel):
    """Excel 导入结果响应"""
    created_count: int = Field(0, description="新增数量")
    updated_count: int = Field(0, description="更新数量")
    total: int = Field(0, description="处理总数")
