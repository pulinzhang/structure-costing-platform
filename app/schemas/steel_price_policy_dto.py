"""
钢价政策数据传输对象
用于 Repository 层返回结构化数据，避免使用字典
"""

from typing import Optional

from pydantic import BaseModel, Field


class FilterOptions(BaseModel):
    """筛选选项 DTO"""

    years: list[int] = Field(default_factory=list)
    months: list[int] = Field(default_factory=list)
    steel_mills: list[str] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)
    policy_types: list[str] = Field(default_factory=list)
    grade_types: list[str] = Field(default_factory=list)
    grade_values: list[str] = Field(default_factory=list)


class ExportRow(BaseModel):
    """
    导出数据行 DTO（主子表扁平化结构）
    每行代表一个政策主表+阶梯明细组合
    """

    model_config = {"from_attributes": True}

    # 政策主表字段
    policy_id: int
    year: int
    month: int
    steel_mill: str
    category_name: str
    policy_type: str
    grade_type: Optional[str] = None
    grade_value: Optional[str] = None
    base_thickness: Optional[str] = None  # Decimal 转为字符串

    # 阶梯明细字段
    item_id: Optional[int] = None
    target_sub_group: Optional[str] = None
    thick_min: Optional[str] = None  # Decimal 转为字符串
    thick_min_operator: Optional[str] = None
    thick_max: Optional[str] = None  # Decimal 转为字符串
    thick_max_operator: Optional[str] = None
    width_min: Optional[str] = None  # Decimal 转为字符串
    width_min_operator: Optional[str] = None
    width_max: Optional[str] = None  # Decimal 转为字符串
    width_max_operator: Optional[str] = None
    zinc_coating_min: Optional[str] = None  # Decimal 转为字符串
    zinc_coating_min_operator: Optional[str] = None
    zinc_coating_max: Optional[str] = None  # Decimal 转为字符串
    zinc_coating_max_operator: Optional[str] = None
    price_adjustment: Optional[int] = None
    is_base: Optional[int] = None
    sort_order: Optional[int] = None

    # 追溯字段（放在最后）
    excel_filename: Optional[str] = None  # 来源 Excel 文件名
    excel_row: Optional[int] = None  # Excel 行号（1-based）
    excel_col: Optional[int] = None  # Excel 列号（1-based）