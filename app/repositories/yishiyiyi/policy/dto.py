"""
钢价政策 Repository 数据传输对象
用于 Repository 层返回结构化数据，避免使用字典
"""

from pydantic import BaseModel, Field


class PolicyFilterOptions(BaseModel):
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
    grade_type: str | None = None
    grade_value: str | None = None
    base_thickness: str | None = None  # Decimal 转为字符串

    # 阶梯明细字段
    item_id: int | None = None
    target_sub_group: str | None = None
    thick_min: str | None = None  # Decimal 转为字符串
    thick_min_operator: str | None = None
    thick_max: str | None = None  # Decimal 转为字符串
    thick_max_operator: str | None = None
    width_min: str | None = None  # Decimal 转为字符串
    width_min_operator: str | None = None
    width_max: str | None = None  # Decimal 转为字符串
    width_max_operator: str | None = None
    zinc_coating_min: str | None = None  # Decimal 转为字符串
    zinc_coating_min_operator: str | None = None
    zinc_coating_max: str | None = None  # Decimal 转为字符串
    zinc_coating_max_operator: str | None = None
    price_adjustment: int | None = None
    is_base: int | None = None
    sort_order: int | None = None

    # 追溯字段（放在最后）
    excel_filename: str | None = None  # 来源 Excel 文件名
    excel_row: int | None = None  # Excel 行号（1-based）
    excel_col: int | None = None  # Excel 列号（1-based）
