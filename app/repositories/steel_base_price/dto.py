"""
钢材基准价格 Repository 数据传输对象
用于 Repository 层返回结构化数据，避免使用字典
"""

from typing import Optional

from pydantic import BaseModel, Field


class FilterOptions(BaseModel):
    """筛选选项 DTO"""

    years: list[int] = Field(default_factory=list)
    months: list[int] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    steel_mills: list[str] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)
    grades: list[str] = Field(default_factory=list)


class ExportRow(BaseModel):
    """
    导出数据行 DTO（扁平化结构）
    """

    model_config = {"from_attributes": True}

    id: int
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thick: Optional[str] = None  # Decimal 转为字符串
    width: Optional[str] = None  # Decimal 转为字符串
    base_price: Optional[str] = None  # Decimal 转为字符串
    processing_fee: Optional[str] = None  # Decimal 转为字符串
    excel_filename: Optional[str] = None
    sheet_name: Optional[str] = None
    excel_row: Optional[int] = None
    remark: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
