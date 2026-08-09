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

from pydantic import BaseModel, Field, field_serializer


def decimal_to_float(value: Decimal | float | None) -> Optional[float]:
    """Decimal 类型转 float 序列化器"""
    if isinstance(value, Decimal):
        return float(value)
    return value


def datetime_to_str(value: datetime | None) -> Optional[str]:
    """datetime 类型转字符串序列化器"""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class SteelBasePriceResponse(BaseModel):
    """
    钢材基准价格响应 VO

    最佳实践要点：
    1. model_config = {"from_attributes": True} 启用 ORM 集成
    2. 使用 @field_serializer 替代 @property 或 to_dict
    3. Decimal → float, datetime → str 由序列化器处理
    """

    model_config = {"from_attributes": True}

    id: int
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thick: Optional[float] = None  # Decimal → float
    width: Optional[float] = None  # Decimal → float
    base_price: Optional[float] = None  # Decimal → float
    processing_fee: Optional[float] = None  # Decimal → float
    spec: Optional[str] = None
    excel_filename: Optional[str] = None
    sheet_name: Optional[str] = None
    excel_row: Optional[int] = None
    excel_col: Optional[int] = None
    remark: Optional[str] = None
    created_at: Optional[str] = None  # datetime → str
    updated_at: Optional[str] = None  # datetime → str

    @field_serializer("thick", "width", "base_price", "processing_fee")
    def serialize_decimal(self, value: Decimal | float | None) -> Optional[float]:
        """Decimal → float 序列化"""
        return decimal_to_float(value)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> Optional[str]:
        """datetime → ISO 字符串序列化"""
        return datetime_to_str(value)


class SteelBasePriceImportResultResponse(BaseModel):
    """Excel 导入结果响应"""
    filename: str
    created_count: int = 0
    updated_count: int = 0
    total: int = 0
    warnings: Optional[list[str]] = None
    errors: Optional[list[str]] = None


class FilterOptionsVO(BaseModel):
    """筛选下拉选项响应 VO"""
    years: list[int] = Field(default_factory=list)
    months: list[int] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    steel_mills: list[str] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)
    grades: list[str] = Field(default_factory=list)
    specs: list[str] = Field(default_factory=list)