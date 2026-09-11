"""
钢价政策 VO - 返回给前端的数据结构
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from app.common.money import Q2, optional_format_money
from app.common.timezone import datetime_to_iso


class PolicyOptionsResponse(BaseModel):
    """政策筛选下拉选项"""

    years: list[int] = Field(default_factory=list)
    months: list[int] = Field(default_factory=list)
    steel_mills: list[str] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)
    policy_types: list[str] = Field(default_factory=list)
    grade_types: list[str] = Field(default_factory=list)
    grade_values: list[str] = Field(default_factory=list)


# ============================
# 阶梯明细 VO
# ============================


class LadderItemResponse(BaseModel):
    """阶梯明细响应"""

    id: int
    policy_id: int
    target_sub_group: str | None = None

    thick_min: Decimal | None = None
    thick_min_operator: str | None = None
    thick_max: Decimal | None = None
    thick_max_operator: str | None = None

    width_min: Decimal | None = None
    width_min_operator: str | None = None
    width_max: Decimal | None = None
    width_max_operator: str | None = None

    zinc_coating_min: Decimal | None = None
    zinc_coating_min_operator: str | None = None
    zinc_coating_max: Decimal | None = None
    zinc_coating_max_operator: str | None = None

    price_adjustment: int = 0
    is_base: int = 0
    sort_order: int = 0
    created_by: str | None = None
    updated_by: str | None = None

    @field_serializer(
        "thick_min",
        "thick_max",
        "width_min",
        "width_max",
        "zinc_coating_min",
        "zinc_coating_max",
    )
    def serialize_decimal(self, value: Decimal | float | None) -> str | None:
        return optional_format_money(value, Q2, 2, allow_negative=True)

    model_config = {"from_attributes": True}


# ============================
# 政策主表 VO
# ============================


class PolicyListResponse(BaseModel):
    """政策列表响应（不含明细）"""

    id: int
    year: int
    month: int
    steel_mill: str
    category_name: str
    policy_type: str
    grade_type: str | None = None
    grade_value: str | None = None
    base_thickness: Decimal | None = None
    item_count: int = 0
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("base_thickness")
    def serialize_base_thickness(self, value: Decimal | float | None) -> str | None:
        return optional_format_money(value, Q2, 2, allow_negative=True)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class PolicyDetailResponse(BaseModel):
    """政策详情响应（包含完整阶梯明细）"""

    id: int
    year: int
    month: int
    steel_mill: str
    category_name: str
    policy_type: str
    grade_type: str | None = None
    grade_value: str | None = None
    base_thickness: Decimal | None = None
    items: list[LadderItemResponse] = []
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("base_thickness")
    def serialize_base_thickness(self, value: Decimal | float | None) -> str | None:
        return optional_format_money(value, Q2, 2, allow_negative=True)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


# ============================
# 阶梯匹配 VO
# ============================


class MatchedLadderItem(BaseModel):
    """匹配命中的阶梯明细"""

    id: int
    target_sub_group: str | None = None

    thick_min: Decimal | None = None
    thick_min_operator: str | None = None
    thick_max: Decimal | None = None
    thick_max_operator: str | None = None

    width_min: Decimal | None = None
    width_min_operator: str | None = None
    width_max: Decimal | None = None
    width_max_operator: str | None = None

    zinc_coating_min: Decimal | None = None
    zinc_coating_min_operator: str | None = None
    zinc_coating_max: Decimal | None = None
    zinc_coating_max_operator: str | None = None

    price_adjustment: int = 0
    is_base: int = 0
    sort_order: int = 0

    @field_serializer(
        "thick_min",
        "thick_max",
        "width_min",
        "width_max",
        "zinc_coating_min",
        "zinc_coating_max",
    )
    def serialize_decimal(self, value: Decimal | float | None) -> str | None:
        return optional_format_money(value, Q2, 2, allow_negative=True)

    model_config = {"from_attributes": True}


class PolicyMatchResponse(BaseModel):
    """阶梯匹配结果响应"""

    matched: bool = Field(False, description="是否命中阶梯")
    policy_id: int | None = Field(None, description="命中的政策 ID")
    item: MatchedLadderItem | None = Field(None, description="命中的阶梯明细")
    price_adjustment: int | None = Field(None, description="加减价金额（元/吨）")


# ============================
# 导入/导出 VO
# ============================


class ImportResultResponse(BaseModel):
    """Excel 导入结果响应"""

    created_count: int = Field(0, description="新增数量")
    updated_count: int = Field(0, description="更新数量")
    skipped_count: int = Field(0, description="跳过数量")
    total: int = Field(0, description="处理总数")


class ExportRow(BaseModel):
    """导出数据行 VO（主子表扁平化结构）"""

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
    base_thickness: str | None = None

    # 阶梯明细字段
    item_id: int | None = None
    target_sub_group: str | None = None
    thick_min: str | None = None
    thick_min_operator: str | None = None
    thick_max: str | None = None
    thick_max_operator: str | None = None
    width_min: str | None = None
    width_min_operator: str | None = None
    width_max: str | None = None
    width_max_operator: str | None = None
    zinc_coating_min: str | None = None
    zinc_coating_min_operator: str | None = None
    zinc_coating_max: str | None = None
    zinc_coating_max_operator: str | None = None
    price_adjustment: int | None = None
    is_base: int | None = None
    sort_order: int | None = None

    # 追溯字段
    excel_filename: str | None = None
    excel_row: int | None = None
    excel_col: int | None = None
