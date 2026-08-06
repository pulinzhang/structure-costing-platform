"""
钢价政策请求与响应 DTO
全程使用 Decimal 表示尺寸和金额，绝不转换为 float
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================
# 枚举定义
# ============================

class PolicyType(str, Enum):
    """政策类型枚举"""
    THICKNESS = "THICKNESS"
    WIDTH = "WIDTH"
    THICKNESS_WIDTH = "THICKNESS_WIDTH"  # 厚度加宽度（同时约束厚度和宽度）


class GradeType(str, Enum):
    """grade_value 的语义类型枚举"""
    GRADE = "GRADE"           # 钢种牌号（如 DC01、DX51D+Z）
    WIDTH_RANGE = "WIDTH_RANGE"  # 宽度范围（如 700≤W<900）
    CATEGORY = "CATEGORY"     # 钢材大类（如 冷轧钢），用于通用宽度加价


class Operator(str, Enum):
    """区间操作符枚举"""
    GTE = ">="   # 大于等于
    GT = ">"     # 大于
    LTE = "<="   # 小于等于
    LT = "<"     # 小于


# ============================
# 辅助函数
# ============================

def _strip(v: Optional[str]) -> Optional[str]:
    """去除首尾空白，无意义时返回 None"""
    if v is None:
        return None
    v = v.strip()
    return v if v else None


def _decimal_str(v: Optional[Decimal | float | int | str]) -> Optional[Decimal]:
    """将各种输入转为 Decimal，None 时返回 None"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


# ============================
# 阶梯明细 DTO
# ============================

class LadderItemCreate(BaseModel):
    """阶梯明细创建请求"""
    target_sub_group: Optional[str] = Field(None, max_length=100, description="附加子分组条件")

    # 厚度维度条件（全部允许为空，为空表示不限）
    thick_min: Optional[Decimal] = Field(None, description="厚度下限值（mm）")
    thick_min_operator: Optional[str] = Field(">=", description="厚度下限操作符")
    thick_max: Optional[Decimal] = Field(None, description="厚度上限值（mm）")
    thick_max_operator: Optional[str] = Field("<", description="厚度上限操作符")

    # 宽度维度条件（全部允许为空，为空表示不限）
    width_min: Optional[Decimal] = Field(None, description="宽度下限值（mm）")
    width_min_operator: Optional[str] = Field(">=", description="宽度下限操作符")
    width_max: Optional[Decimal] = Field(None, description="宽度上限值（mm）")
    width_max_operator: Optional[str] = Field("<", description="宽度上限操作符")

    # 锌层克重维度条件（g/m²，全部允许为空）
    zinc_coating_min: Optional[Decimal] = Field(None, description="锌层克重下限值（g/m²）")
    zinc_coating_min_operator: Optional[str] = Field(">=", description="锌层克重下限操作符")
    zinc_coating_max: Optional[Decimal] = Field(None, description="锌层克重上限值（g/m²）")
    zinc_coating_max_operator: Optional[str] = Field("<", description="锌层克重上限操作符")

    # 加减价与排序
    price_adjustment: int = Field(..., description="加减价金额（元/吨，整数）")
    is_base: int = Field(0, description="是否为基准厚度：0=否，1=是")
    sort_order: int = Field(0, description="匹配排序号")

    @field_validator("target_sub_group", mode="before")
    @classmethod
    def strip_target_sub_group(cls, v):
        return _strip(v)

    @model_validator(mode="after")
    def check_at_least_one_dimension(self):
        """明细至少需要指定一个维度条件（厚度或宽度）"""
        has_thick = self.thick_min is not None or self.thick_max is not None
        has_width = self.width_min is not None or self.width_max is not None
        if not has_thick and not has_width:
            raise ValueError("明细至少需要指定一个维度条件（厚度或宽度）")
        return self


class LadderItemUpdate(BaseModel):
    """阶梯明细更新请求"""
    target_sub_group: Optional[str] = Field(None, max_length=100, description="附加子分组条件")

    # 厚度维度条件
    thick_min: Optional[Decimal] = Field(None, description="厚度下限值（mm）")
    thick_min_operator: Optional[str] = Field(None, description="厚度下限操作符")
    thick_max: Optional[Decimal] = Field(None, description="厚度上限值（mm）")
    thick_max_operator: Optional[str] = Field(None, description="厚度上限操作符")

    # 宽度维度条件
    width_min: Optional[Decimal] = Field(None, description="宽度下限值（mm）")
    width_min_operator: Optional[str] = Field(None, description="宽度下限操作符")
    width_max: Optional[Decimal] = Field(None, description="宽度上限值（mm）")
    width_max_operator: Optional[str] = Field(None, description="宽度上限操作符")

    # 加减价与排序
    price_adjustment: Optional[int] = Field(None, description="加减价金额（元/吨）")
    is_base: Optional[int] = Field(None, description="是否为基准厚度：0=否，1=是")
    sort_order: Optional[int] = Field(None, description="匹配排序号")

    @field_validator("target_sub_group", mode="before")
    @classmethod
    def strip_target_sub_group(cls, v):
        return _strip(v)


class LadderItemResponse(BaseModel):
    """阶梯明细响应（全程保持 Decimal 精确表示）"""
    id: int
    policy_id: int
    target_sub_group: Optional[str]

    # 厚度维度
    thick_min: Optional[Decimal]
    thick_min_operator: Optional[str]
    thick_max: Optional[Decimal]
    thick_max_operator: Optional[str]

    # 宽度维度
    width_min: Optional[Decimal]
    width_min_operator: Optional[str]
    width_max: Optional[Decimal]
    width_max_operator: Optional[str]

    # 加减价与标记
    price_adjustment: int
    is_base: int
    sort_order: int

    @field_validator(
        "thick_min", "thick_max", "width_min", "width_max",
        mode="plain",
    )
    @classmethod
    def keep_decimal(cls, v):
        """确保 Decimal 精确传递，不转为 float"""
        return _decimal_str(v)

    model_config = {"from_attributes": True}


# ============================
# 政策主表 DTO
# ============================

class PolicyCreate(BaseModel):
    """政策创建请求"""
    year: int = Field(..., ge=2000, le=2100, description="生效年度")
    month: int = Field(..., ge=1, le=12, description="生效月份（1-12）")
    steel_mill: str = Field(..., min_length=1, max_length=100, description="钢厂名称")
    category_name: str = Field(..., min_length=1, max_length=100, description="钢种大类")
    policy_type: PolicyType = Field(..., description="政策类型：THICKNESS=厚度加减价，WIDTH=宽度加价")
    grade_type: Optional[GradeType] = Field(None, description="grade_value 的语义类型：GRADE/WIDTH_RANGE/CATEGORY")
    grade_value: Optional[str] = Field(None, max_length=100, description="牌号或宽度范围（GRADE 时如 'DC01'，WIDTH_RANGE 时如 '700≤W<900'，CATEGORY 时如 '冷轧钢'）")
    base_thickness: Optional[Decimal] = Field(None, description="基准厚度（仅厚度政策需要）")
    items: list[LadderItemCreate] = Field(..., min_length=1, description="阶梯明细，至少一条")

    @field_validator("steel_mill", "category_name", "grade_value", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return _strip(v)

    @model_validator(mode="after")
    def check_thickness_policy_requires_base(self):
        """THICKNESS 政策必须提供 grade_value 和 base_thickness"""
        if self.policy_type == PolicyType.THICKNESS:
            if not self.grade_value:
                raise ValueError("THICKNESS 政策必须指定 grade_value（牌号）")
            if self.base_thickness is None:
                raise ValueError("THICKNESS 政策必须指定 base_thickness（基准厚度）")
        return self


class PolicyUpdate(BaseModel):
    """政策更新请求（业务主键字段 year/month/steel_mill/category_name/policy_type 不允许变更）"""
    grade_type: Optional[GradeType] = Field(None, description="grade_value 的语义类型")
    grade_value: Optional[str] = Field(None, max_length=100, description="牌号或宽度范围")
    base_thickness: Optional[Decimal] = Field(None, description="基准厚度")
    items: Optional[list[LadderItemCreate]] = Field(None, description="整组替换阶梯明细（传空数组则清空明细）")

    @field_validator("grade_value", mode="before")
    @classmethod
    def strip_grade_value(cls, v):
        return _strip(v)

    @model_validator(mode="after")
    def check_base_thickness_for_thickness_policy(self):
        """THICKNESS 政策若提供 base_thickness 则必须非负"""
        if self.base_thickness is not None and self.base_thickness < 0:
            raise ValueError("base_thickness 不能为负数")
        return self


class PolicyListResponse(BaseModel):
    """政策列表响应（不含明细）"""
    id: int
    year: int
    month: int
    steel_mill: str
    category_name: str
    policy_type: str
    grade_type: Optional[str]
    grade_value: Optional[str]
    base_thickness: Optional[Decimal]
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
    grade_type: Optional[str]
    grade_value: Optional[str]
    base_thickness: Optional[Decimal]
    items: list[LadderItemResponse]
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
# 查询参数 DTO
# ============================

class PolicyQuery(BaseModel):
    """政策分页筛选参数"""
    year: Optional[int] = Field(None, ge=2000, le=2100, description="生效年度")
    month: Optional[int] = Field(None, ge=1, le=12, description="生效月份（1-12）")
    steel_mill: Optional[str] = Field(None, description="钢厂名称")
    category_name: Optional[str] = Field(None, description="钢种大类")
    policy_type: Optional[PolicyType] = Field(None, description="政策类型")
    grade_type: Optional[GradeType] = Field(None, description="grade_value 的语义类型")
    grade_value: Optional[str] = Field(None, description="牌号或宽度范围")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=200, description="每页条数")

    @field_validator("steel_mill", "category_name", "grade_value", mode="before")
    @classmethod
    def strip_query_strings(cls, v):
        return _strip(v)


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
# 阶梯匹配 DTO
# ============================

class PolicyMatchRequest(BaseModel):
    """阶梯匹配请求"""
    year: int = Field(..., ge=2000, le=2100, description="生效年度")
    month: int = Field(..., ge=1, le=12, description="生效月份（1-12）")
    steel_mill: str = Field(..., min_length=1, max_length=100, description="钢厂名称")
    category_name: str = Field(..., min_length=1, max_length=100, description="钢种大类")
    policy_type: PolicyType = Field(..., description="政策类型")
    grade_type: Optional[GradeType] = Field(None, description="grade_value 的语义类型")
    grade_value: Optional[str] = Field(None, max_length=100, description="牌号或宽度范围（THICKNESS 政策必须提供 grade_value）")
    base_thickness: Optional[Decimal] = Field(None, description="基准厚度（THICKNESS 政策必须）")
    target_sub_group: Optional[str] = Field(None, max_length=100, description="附加子分组条件")
    thickness: Optional[Decimal] = Field(None, description="待匹配的厚度值（mm）")
    width: Optional[Decimal] = Field(None, description="待匹配的宽度值（mm）")
    zinc_coating: Optional[int] = Field(None, description="待匹配的锌层克重（g/m²）")

    @field_validator("steel_mill", "category_name", "grade_value", "target_sub_group", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return _strip(v)

    @field_validator("thickness", "width", mode="before")
    @classmethod
    def coerce_dimensions(cls, v):
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        raise ValueError("thickness/width 必须是数字")

    @field_validator("zinc_coating", mode="before")
    @classmethod
    def coerce_zinc_coating(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, (float, str)):
            return int(float(v))
        raise ValueError("zinc_coating 必须是整数")

    @model_validator(mode="after")
    def check_at_least_one_dimension(self):
        """至少需要提供 thickness、width 或 zinc_coating 之一"""
        if self.thickness is None and self.width is None and self.zinc_coating is None:
            raise ValueError("至少需要提供 thickness、width 或 zinc_coating 之一")
        return self

    @model_validator(mode="after")
    def check_thickness_requires(self):
        if self.policy_type == PolicyType.THICKNESS:
            if not self.grade_value:
                raise ValueError("THICKNESS 政策匹配必须提供 grade_value")
            if self.base_thickness is None:
                raise ValueError("THICKNESS 政策匹配必须提供 base_thickness")
        return self


class MatchedLadderItem(BaseModel):
    """匹配命中的阶梯明细"""
    id: int
    target_sub_group: Optional[str]

    # 厚度维度
    thick_min: Optional[Decimal]
    thick_min_operator: Optional[str]
    thick_max: Optional[Decimal]
    thick_max_operator: Optional[str]

    # 宽度维度
    width_min: Optional[Decimal]
    width_min_operator: Optional[str]
    width_max: Optional[Decimal]
    width_max_operator: Optional[str]

    # 加减价与标记
    price_adjustment: int
    is_base: int
    sort_order: int

    @field_validator(
        "thick_min", "thick_max", "width_min", "width_max",
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


class ImportResultResponse(BaseModel):
    """Excel 导入结果响应"""
    created_count: int = Field(0, description="新增数量")
    updated_count: int = Field(0, description="更新数量")
    skipped_count: int = Field(0, description="跳过数量")
    total: int = Field(0, description="处理总数")
