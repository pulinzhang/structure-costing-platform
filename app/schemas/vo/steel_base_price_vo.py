"""
钢材基准价格 VO - 返回给前端的数据结构

使用 Pydantic v2 官方推荐的 ORM 集成方式：
- model_config = ConfigDict(from_attributes=True)
- model_validate() 从 ORM 对象转换
- @field_serializer 序列化 Decimal/Datetime
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.money import Q2, optional_format_money
from app.common.timezone import datetime_to_iso


class SteelBasePriceResponse(BaseModel):
    """钢材基准价格响应 VO"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thick: Decimal | None = None
    width: Decimal | None = None
    base_price: Decimal | None = None
    processing_fee: Decimal | None = None
    spec: str | None = None
    excel_filename: str | None = None
    sheet_name: str | None = None
    excel_row: int | None = None
    excel_col: int | None = None
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("thick", "width")
    def serialize_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)

    @field_serializer("base_price", "processing_fee")
    def serialize_price(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class SteelBasePriceImportResultResponse(BaseModel):
    """Excel 导入结果响应"""

    filename: str
    created_count: int = 0
    updated_count: int = 0
    total: int = 0
    warnings: list[str] | None = None
    errors: list[str] | None = None


class SteelBasePriceExportRow(BaseModel):
    """导出预览行 VO"""

    model_config = ConfigDict(from_attributes=True)

    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thick: Decimal | None = None
    width: Decimal | None = None
    base_price: Decimal | None = None
    processing_fee: Decimal | None = None
    spec: str | None = None
    excel_filename: str | None = None
    sheet_name: str | None = None
    excel_row: int | None = None
    excel_col: int | None = None

    @field_serializer("thick", "width")
    def serialize_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)

    @field_serializer("base_price", "processing_fee")
    def serialize_price(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)


class SteelBasePriceFilterOptionsVO(BaseModel):
    """筛选选项 VO（API 响应用）"""

    years: list[int] = []
    months: list[int] = []
    locations: list[str] = []
    steel_mills: list[str] = []
    category_names: list[str] = []
    grades: list[str] = []
    specs: list[str] = []


class SteelBasePriceBatchDeleteResultVO(BaseModel):
    """按年+月（及可选基地/钢厂）批量删除结果"""

    year: int
    month: int
    message: str = ""
