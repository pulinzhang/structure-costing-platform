"""
钢材基准价格 VO - 返回给前端的数据结构

使用 Pydantic v2 官方推荐的 ORM 集成方式：
- model_config = {"from_attributes": True}
- model_validate() 从 ORM 对象转换
- @field_serializer 序列化 Decimal/Datetime
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_serializer

from app.common.money import Q2, optional_format_money


def datetime_to_str(value: datetime | None) -> Optional[str]:
    """datetime 类型转字符串序列化器"""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class SteelBasePriceResponse(BaseModel):
    """钢材基准价格响应 VO"""

    model_config = {"from_attributes": True}

    id: int
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thick: Optional[Decimal] = None
    width: Optional[Decimal] = None
    base_price: Optional[Decimal] = None
    processing_fee: Optional[Decimal] = None
    spec: Optional[str] = None
    excel_filename: Optional[str] = None
    sheet_name: Optional[str] = None
    excel_row: Optional[int] = None
    excel_col: Optional[int] = None
    remark: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("thick", "width")
    def serialize_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)

    @field_serializer("base_price", "processing_fee")
    def serialize_price(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> Optional[str]:
        return datetime_to_str(value)


class SteelBasePriceImportResultResponse(BaseModel):
    """Excel 导入结果响应"""
    filename: str
    created_count: int = 0
    updated_count: int = 0
    total: int = 0
    warnings: Optional[list[str]] = None
    errors: Optional[list[str]] = None


class SteelBasePriceExportRow(BaseModel):
    """导出预览行 VO"""
    model_config = {"from_attributes": True}

    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thick: Optional[Decimal] = None
    width: Optional[Decimal] = None
    base_price: Optional[Decimal] = None
    processing_fee: Optional[Decimal] = None
    spec: Optional[str] = None
    excel_filename: Optional[str] = None
    sheet_name: Optional[str] = None
    excel_row: Optional[int] = None
    excel_col: Optional[int] = None

    @field_serializer("thick", "width")
    def serialize_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)

    @field_serializer("base_price", "processing_fee")
    def serialize_price(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)


class FilterOptionsVO(BaseModel):
    """筛选选项 VO（API 响应用）"""
    years: list[int] = []
    months: list[int] = []
    locations: list[str] = []
    steel_mills: list[str] = []
    category_names: list[str] = []
    grades: list[str] = []
    specs: list[str] = []
