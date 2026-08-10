"""
钢价政策 VO - 返回给前端的数据结构
所有枚举和 Response 类型均定义于此，与 DTO（Request）分离
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ============================
# 枚举定义（与 DTO 共享一份）
# ============================


class PolicyType(str, Enum):
    """政策类型枚举"""
    THICKNESS = "THICKNESS"
    WIDTH = "WIDTH"
    THICKNESS_WIDTH = "THICKNESS_WIDTH"


class GradeType(str, Enum):
    """grade_value 的语义类型枚举"""
    GRADE = "GRADE"
    WIDTH_RANGE = "WIDTH_RANGE"
    CATEGORY = "CATEGORY"


class Operator(str, Enum):
    """区间操作符枚举"""
    GTE = ">="
    GT = ">"
    LTE = "<="
    LT = "<"


# ============================
# 辅助函数
# ============================


def _decimal_str(v: Optional[Decimal | float | int | str]) -> Optional[Decimal]:
    """将各种输入转为 Decimal，None 时返回 None"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


# ============================
# 筛选选项 VO
# ============================


class FilterOptions(BaseModel):
    """筛选选项（Repository 层 → Service → PolicyOptionsResponse 的中间结构）"""
    years: list[int] = Field(default_factory=list)
    months: list[int] = Field(default_factory=list)
    steel_mills: list[str] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)
    policy_types: list[str] = Field(default_factory=list)
    grade_types: list[str] = Field(default_factory=list)
    grade_values: list[str] = Field(default_factory=list)


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
    target_sub_group: Optional[str] = None

    thick_min: Optional[Decimal] = None
    thick_min_operator: Optional[str] = None
    thick_max: Optional[Decimal] = None
    thick_max_operator: Optional[str] = None

    width_min: Optional[Decimal] = None
    width_min_operator: Optional[str] = None
    width_max: Optional[Decimal] = None
    width_max_operator: Optional[str] = None

    zinc_coating_min: Optional[Decimal] = None
    zinc_coating_min_operator: Optional[str] = None
    zinc_coating_max: Optional[Decimal] = None
    zinc_coating_max_operator: Optional[str] = None

    price_adjustment: int = 0
    is_base: int = 0
    sort_order: int = 0

    @field_validator(
        "thick_min", "thick_max",
        "width_min", "width_max",
        "zinc_coating_min", "zinc_coating_max",
        mode="plain",
    )
    @classmethod
    def keep_decimal(cls, v):
        return _decimal_str(v)

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
    grade_type: Optional[str] = None
    grade_value: Optional[str] = None
    base_thickness: Optional[Decimal] = None
    item_count: int = 0
    created_at: datetime
    updated_at: datetime

    @field_validator("base_thickness", mode="plain")
    @classmethod
    def keep_decimal(cls, v):
        return _decimal_str(v)

    @field_validator("created_at", "updated_at")
    @classmethod
    def iso_datetime(cls, v: datetime) -> str:
        return v.isoformat() if v else None

    model_config = {"from_attributes": True}


class PolicyDetailResponse(BaseModel):
    """政策详情响应（包含完整阶梯明细）"""
    id: int
    year: int
    month: int
    steel_mill: str
    category_name: str
    policy_type: str
    grade_type: Optional[str] = None
    grade_value: Optional[str] = None
    base_thickness: Optional[Decimal] = None
    items: list[LadderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("base_thickness", mode="plain")
    @classmethod
    def keep_decimal(cls, v):
        return _decimal_str(v)

    @field_validator("created_at", "updated_at")
    @classmethod
    def iso_datetime(cls, v: datetime) -> str:
        return v.isoformat() if v else None

    model_config = {"from_attributes": True}


# ============================
# 阶梯匹配 VO
# ============================


class MatchedLadderItem(BaseModel):
    """匹配命中的阶梯明细"""
    id: int
    target_sub_group: Optional[str] = None

    thick_min: Optional[Decimal] = None
    thick_min_operator: Optional[str] = None
    thick_max: Optional[Decimal] = None
    thick_max_operator: Optional[str] = None

    width_min: Optional[Decimal] = None
    width_min_operator: Optional[str] = None
    width_max: Optional[Decimal] = None
    width_max_operator: Optional[str] = None

    zinc_coating_min: Optional[Decimal] = None
    zinc_coating_min_operator: Optional[str] = None
    zinc_coating_max: Optional[Decimal] = None
    zinc_coating_max_operator: Optional[str] = None

    price_adjustment: int = 0
    is_base: int = 0
    sort_order: int = 0

    @field_validator(
        "thick_min", "thick_max",
        "width_min", "width_max",
        "zinc_coating_min", "zinc_coating_max",
        mode="plain",
    )
    @classmethod
    def keep_decimal(cls, v):
        return _decimal_str(v)

    model_config = {"from_attributes": True}


class PolicyMatchResponse(BaseModel):
    """阶梯匹配结果响应"""
    matched: bool = Field(False, description="是否命中阶梯")
    policy_id: Optional[int] = Field(None, description="命中的政策 ID")
    item: Optional[MatchedLadderItem] = Field(None, description="命中的阶梯明细")
    price_adjustment: Optional[int] = Field(None, description="加减价金额（元/吨）")


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
    grade_type: Optional[str] = None
    grade_value: Optional[str] = None
    base_thickness: Optional[str] = None

    # 阶梯明细字段
    item_id: Optional[int] = None
    target_sub_group: Optional[str] = None
    thick_min: Optional[str] = None
    thick_min_operator: Optional[str] = None
    thick_max: Optional[str] = None
    thick_max_operator: Optional[str] = None
    width_min: Optional[str] = None
    width_min_operator: Optional[str] = None
    width_max: Optional[str] = None
    width_max_operator: Optional[str] = None
    zinc_coating_min: Optional[str] = None
    zinc_coating_min_operator: Optional[str] = None
    zinc_coating_max: Optional[str] = None
    zinc_coating_max_operator: Optional[str] = None
    price_adjustment: Optional[int] = None
    is_base: Optional[int] = None
    sort_order: Optional[int] = None

    # 追溯字段
    excel_filename: Optional[str] = None
    excel_row: Optional[int] = None
    excel_col: Optional[int] = None


# ============================
# 兼容旧引用（避免前端直接引用 DTO 产生困惑）
# ============================

# 以下两个类保留于此文件中，供直接引用 Response 的场景使用
# 注意：Router 应统一使用上面已命名的 Response 类型


class SteelPricePolicyResponse(BaseModel):
    """钢价政策响应 VO（简化版，与 PolicyDetailResponse 字段重叠，仅保留用于特殊场景）"""

    model_config = {"from_attributes": True}

    id: int
    year: int
    month: int
    steel_mill: str
    category_name: str
    policy_type: str
    grade_type: Optional[str] = None
    grade_value: Optional[str] = None
    base_thickness: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SteelPricePolicyItemResponse(BaseModel):
    """钢价政策阶梯明细响应 VO（简化版，仅保留用于特殊场景）"""

    model_config = {"from_attributes": True}

    id: int
    policy_id: int
    target_sub_group: Optional[str] = None
    thick_min: Optional[str] = None
    thick_min_operator: Optional[str] = None
    thick_max: Optional[str] = None
    thick_max_operator: Optional[str] = None
    width_min: Optional[str] = None
    width_min_operator: Optional[str] = None
    width_max: Optional[str] = None
    width_max_operator: Optional[str] = None
    zinc_coating_min: Optional[str] = None
    zinc_coating_min_operator: Optional[str] = None
    zinc_coating_max: Optional[str] = None
    zinc_coating_max_operator: Optional[str] = None
    price_adjustment: Optional[int] = None
    is_base: Optional[int] = None
    sort_order: Optional[int] = None
