"""
钢材基准价格 Repository 数据传输对象
用于 Repository 层返回结构化数据，避免使用字典
"""

from pydantic import BaseModel, Field


class FilterOptions(BaseModel):
    """筛选选项 DTO"""

    years: list[int] = Field(default_factory=list)
    months: list[int] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    steel_mills: list[str] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)
    grades: list[str] = Field(default_factory=list)
    specs: list[str] = Field(default_factory=list)


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
    thick: str | None = None  # Decimal 转为字符串
    width: str | None = None  # Decimal 转为字符串
    base_price: str | None = None  # Decimal 转为字符串
    processing_fee: str | None = None  # Decimal 转为字符串
    excel_filename: str | None = None
    sheet_name: str | None = None
    excel_row: int | None = None
    remark: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
