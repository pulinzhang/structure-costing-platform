"""
钢价政策 DTO - 请求参数数据结构
仅包含接收前端/内部参数的 Request 类型，不含任何 Response 类型
Response 类型统一放 vo/steel_price_policy_vo.py
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
    MONTH_MAX,
    MONTH_MIN,
)

# ============================
# 枚举定义
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


# ============================
# 辅助函数
# ============================


def _strip(v: str | None) -> str | None:
    """去除首尾空白，无意义时返回 None"""
    if v is None:
        return None
    v = v.strip()
    return v if v else None


# ============================
# 阶梯明细 DTO（Request）
# ============================


class LadderItemCreate(BaseModel):
    """阶梯明细创建请求"""

    target_sub_group: str | None = Field(None, max_length=100, description="附加子分组条件")

    thick_min: Decimal | None = Field(None, description="厚度下限值（mm）")
    thick_min_operator: str | None = Field(">=", description="厚度下限操作符")
    thick_max: Decimal | None = Field(None, description="厚度上限值（mm）")
    thick_max_operator: str | None = Field("<", description="厚度上限操作符")

    width_min: Decimal | None = Field(None, description="宽度下限值（mm）")
    width_min_operator: str | None = Field(">=", description="宽度下限操作符")
    width_max: Decimal | None = Field(None, description="宽度上限值（mm）")
    width_max_operator: str | None = Field("<", description="宽度上限操作符")

    zinc_coating_min: Decimal | None = Field(None, description="锌层克重下限值（g/m²）")
    zinc_coating_min_operator: str | None = Field(">=", description="锌层克重下限操作符")
    zinc_coating_max: Decimal | None = Field(None, description="锌层克重上限值（g/m²）")
    zinc_coating_max_operator: str | None = Field("<", description="锌层克重上限操作符")

    price_adjustment: int = Field(..., description="加减价金额（元/吨，整数）")
    is_base: int = Field(0, description="是否为基准厚度：0=否，1=是")
    sort_order: int = Field(0, description="匹配排序号")

    @field_validator("target_sub_group", mode="before")
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_target_sub_group(cls, v: Any) -> Any:
        return _strip(v)

    @model_validator(mode="after")
    def check_at_least_one_dimension(self) -> Self:
        has_thick = self.thick_min is not None or self.thick_max is not None
        has_width = self.width_min is not None or self.width_max is not None
        if not has_thick and not has_width:
            raise ValueError("明细至少需要指定一个维度条件（厚度或宽度）")
        return self


class LadderItemUpdate(BaseModel):
    """阶梯明细更新请求"""

    target_sub_group: str | None = Field(None, max_length=100, description="附加子分组条件")

    thick_min: Decimal | None = Field(None, description="厚度下限值（mm）")
    thick_min_operator: str | None = Field(None, description="厚度下限操作符")
    thick_max: Decimal | None = Field(None, description="厚度上限值（mm）")
    thick_max_operator: str | None = Field(None, description="厚度上限操作符")

    width_min: Decimal | None = Field(None, description="宽度下限值（mm）")
    width_min_operator: str | None = Field(None, description="宽度下限操作符")
    width_max: Decimal | None = Field(None, description="宽度上限值（mm）")
    width_max_operator: str | None = Field(None, description="宽度上限操作符")

    price_adjustment: int | None = Field(None, description="加减价金额（元/吨）")
    is_base: int | None = Field(None, description="是否为基准厚度：0=否，1=是")
    sort_order: int | None = Field(None, description="匹配排序号")

    @field_validator("target_sub_group", mode="before")
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_target_sub_group(cls, v: Any) -> Any:
        return _strip(v)


# ============================
# 政策主表 DTO（Request）
# ============================


class PolicyCreate(BaseModel):
    """政策创建请求"""

    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="生效年度")
    month: int = Field(..., ge=MONTH_MIN, le=MONTH_MAX, description="生效月份（1-12）")
    steel_mill: str = Field(..., min_length=1, max_length=100, description="钢厂名称")
    category_name: str = Field(..., min_length=1, max_length=100, description="钢种大类")
    policy_type: PolicyType = Field(..., description="政策类型")
    grade_type: GradeType | None = Field(None, description="grade_value 的语义类型")
    grade_value: str | None = Field(None, max_length=100, description="牌号或宽度范围")
    base_thickness: Decimal | None = Field(None, description="基准厚度（仅厚度政策需要）")
    items: list[LadderItemCreate] = Field(..., min_length=1, description="阶梯明细，至少一条")

    @field_validator("steel_mill", "category_name", "grade_value", mode="before")
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_strings(cls, v: Any) -> Any:
        return _strip(v)

    @model_validator(mode="after")
    def check_thickness_policy_requires_base(self) -> Self:
        if self.policy_type == PolicyType.THICKNESS:
            if not self.grade_value:
                raise ValueError("THICKNESS 政策必须指定 grade_value（牌号）")
            if self.base_thickness is None:
                raise ValueError("THICKNESS 政策必须指定 base_thickness（基准厚度）")
        return self


class PolicyUpdate(BaseModel):
    """政策更新请求"""

    grade_type: GradeType | None = Field(None, description="grade_value 的语义类型")
    grade_value: str | None = Field(None, max_length=100, description="牌号或宽度范围")
    base_thickness: Decimal | None = Field(None, description="基准厚度")
    items: list[LadderItemCreate] | None = Field(None, description="整组替换阶梯明细")

    @field_validator("grade_value", mode="before")
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_grade_value(cls, v: Any) -> Any:
        return _strip(v)

    @model_validator(mode="after")
    def check_base_thickness_for_thickness_policy(self) -> Self:
        if self.base_thickness is not None and self.base_thickness < 0:
            raise ValueError("base_thickness 不能为负数")
        return self


# ============================
# 查询参数 DTO
# ============================


class PolicyQuery(BaseModel):
    """政策分页筛选参数"""

    year: int | None = Field(None, ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="生效年度")
    month: int | None = Field(None, ge=MONTH_MIN, le=MONTH_MAX, description="生效月份（1-12）")
    steel_mill: str | None = Field(None, description="钢厂名称")
    category_name: str | None = Field(None, description="钢种大类")
    policy_type: PolicyType | None = Field(None, description="政策类型")
    grade_type: GradeType | None = Field(None, description="grade_value 的语义类型")
    grade_value: str | None = Field(None, description="牌号或宽度范围")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=200, description="每页条数")

    @field_validator("steel_mill", "category_name", "grade_value", mode="before")
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_query_strings(cls, v: Any) -> Any:
        return _strip(v)


class PolicySheetNameQuery(BaseModel):
    """表页下拉：只按它前面的年度、月份、钢厂去重。"""

    year: int | None = Field(None, ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="生效年度")
    month: int | None = Field(None, ge=MONTH_MIN, le=MONTH_MAX, description="生效月份（1-12）")
    steel_mill: str | None = Field(None, description="钢厂名称")

    @field_validator("steel_mill", mode="before")
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_sheet_query_strings(cls, v: Any) -> Any:
        return _strip(v)


class PolicyExportQuery(BaseModel):
    """加减价政策列表筛选：年度、月份、钢厂、表页、钢种大类、牌号。"""

    year: int | None = Field(None, ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="生效年度")
    month: int | None = Field(None, ge=MONTH_MIN, le=MONTH_MAX, description="生效月份（1-12）")
    steel_mill: str | None = Field(None, description="钢厂名称")
    sheet_name: str | None = Field(None, max_length=100, description="来源 Excel 工作表名")
    category_name: str | None = Field(None, description="钢种大类：冷轧/镀锌/酸洗")
    grade_value: str | None = Field(None, description="牌号（经档案解析为大类后筛选政策）")

    @field_validator("steel_mill", "sheet_name", "category_name", "grade_value", mode="before")
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_export_strings(cls, v: Any) -> Any:
        return _strip(v)


class PolicyExportPreviewQuery(PolicyExportQuery):
    """加减价政策列表预览分页。"""

    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=5000, description="每页条数")


# ============================
# 阶梯匹配 DTO（Request）
# ============================


class PolicyMatchRequest(BaseModel):
    """阶梯匹配请求"""

    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="生效年度")
    month: int = Field(..., ge=MONTH_MIN, le=MONTH_MAX, description="生效月份（1-12）")
    steel_mill: str = Field(..., min_length=1, max_length=100, description="钢厂名称")
    category_name: str = Field(..., min_length=1, max_length=100, description="钢种大类")
    policy_type: PolicyType = Field(..., description="政策类型")
    grade_type: GradeType | None = Field(None, description="grade_value 的语义类型")
    grade_value: str | None = Field(None, max_length=100, description="牌号或宽度范围")
    base_thickness: Decimal | None = Field(None, description="基准厚度")
    target_sub_group: str | None = Field(None, max_length=100, description="附加子分组条件")
    thickness: Decimal | None = Field(None, description="待匹配的厚度值（mm）")
    width: Decimal | None = Field(None, description="待匹配的宽度值（mm）")
    zinc_coating: int | None = Field(None, description="待匹配的锌层克重（g/m²）")

    @field_validator(
        "steel_mill", "category_name", "grade_value", "target_sub_group", mode="before"
    )
    @classmethod
    # 非字符串要原样交给后面的校验，收成字符串会改掉现在的报错。
    def strip_strings(cls, v: Any) -> Any:
        return _strip(v)

    @field_validator("thickness", "width", mode="before")
    @classmethod
    def coerce_dimensions(cls, v: object) -> Decimal | None:
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        if isinstance(v, int | float | str):
            return Decimal(str(v))
        raise ValueError("thickness/width 必须是数字")

    @field_validator("zinc_coating", mode="before")
    @classmethod
    def coerce_zinc_coating(cls, v: object) -> int | None:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float | str):
            return int(float(v))
        raise ValueError("zinc_coating 必须是整数")

    @model_validator(mode="after")
    def check_at_least_one_dimension(self) -> Self:
        if self.thickness is None and self.width is None and self.zinc_coating is None:
            raise ValueError("至少需要提供 thickness、width 或 zinc_coating 之一")
        return self

    @model_validator(mode="after")
    def check_thickness_requires(self) -> Self:
        if self.policy_type == PolicyType.THICKNESS:
            if not self.grade_value:
                raise ValueError("THICKNESS 政策匹配必须提供 grade_value")
            if self.base_thickness is None:
                raise ValueError("THICKNESS 政策匹配必须提供 base_thickness")
        return self


# ============================
# Repository 写入载荷
# ============================


@dataclass(slots=True)
class SteelPricePolicyWrite:
    """政策主表新建（含 Excel 文件名与审计人；不含阶梯明细）。"""

    year: int
    month: int
    steel_mill: str
    category_name: str
    policy_type: str
    steel_mill_id: int
    grade_type: str | None = None
    grade_value: str | None = None
    base_thickness: Decimal | None = None
    excel_filename: str | None = None
    sheet_name: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


@dataclass(slots=True)
class SteelPriceLadderItemWrite:
    """阶梯明细新建（policy_id 由 Repository 写入）。"""

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
    excel_row: int | None = None
    excel_col: int | None = None
    created_by: str | None = None
    updated_by: str | None = None
