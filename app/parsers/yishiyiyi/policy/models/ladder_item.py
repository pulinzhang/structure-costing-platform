"""阶梯项模型。

表示一个厚度+宽度区间对应的加减价。
当某一维度字段全部为 None 时，该维度不参与匹配限制。
例如: 厚度 >= 1.0 < 1.2, 宽度 >= 900 < 1600 → 加价 +100 元/吨
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional


@dataclass
class ParsedLadderItem:
    """双维度阶梯明细"""

    # 附加分组条件（如按钢种分组）
    target_sub_group: Optional[str] = None

    # 厚度维度
    thick_min: Optional[Decimal] = None
    thick_min_operator: Optional[str] = ">="
    thick_max: Optional[Decimal] = None
    thick_max_operator: Optional[str] = "<"

    # 宽度维度
    width_min: Optional[Decimal] = None
    width_min_operator: Optional[str] = ">="
    width_max: Optional[Decimal] = None
    width_max_operator: Optional[str] = "<"

    # 锌层克重维度（g/m²）
    zinc_coating_min: Optional[Decimal] = None
    zinc_coating_min_operator: Optional[str] = ">="
    zinc_coating_max: Optional[Decimal] = None
    zinc_coating_max_operator: Optional[str] = "<"

    # 加减价
    price_adjustment: int = 0
    is_base: bool = False  # 是否为基准厚度（加价为0）
    sort_order: int = 0

    # Excel 原始位置（用于测试核对）
    excel_row: Optional[int] = None
    excel_col: Optional[int] = None

    @property
    def has_thickness_condition(self) -> bool:
        """是否有厚度条件"""
        return self.thick_min is not None or self.thick_max is not None

    @property
    def has_width_condition(self) -> bool:
        """是否有宽度条件"""
        return self.width_min is not None or self.width_max is not None

    @property
    def has_zinc_coating_condition(self) -> bool:
        """是否有锌层克重条件"""
        return self.zinc_coating_min is not None or self.zinc_coating_max is not None

    @property
    def has_any_condition(self) -> bool:
        """是否有任一维度条件"""
        return self.has_thickness_condition or self.has_width_condition or self.has_zinc_coating_condition

    def model_dump(self) -> dict[str, Any]:
        """返回字典格式，兼容 Pydantic 接口"""
        return {
            "target_sub_group": self.target_sub_group,
            # 厚度维度
            "thick_min": float(self.thick_min) if self.thick_min is not None else None,
            "thick_min_operator": self.thick_min_operator,
            "thick_max": float(self.thick_max) if self.thick_max is not None else None,
            "thick_max_operator": self.thick_max_operator,
            # 宽度维度
            "width_min": float(self.width_min) if self.width_min is not None else None,
            "width_min_operator": self.width_min_operator,
            "width_max": float(self.width_max) if self.width_max is not None else None,
            "width_max_operator": self.width_max_operator,
            # 锌层克重维度
            "zinc_coating_min": float(self.zinc_coating_min) if self.zinc_coating_min is not None else None,
            "zinc_coating_min_operator": self.zinc_coating_min_operator,
            "zinc_coating_max": float(self.zinc_coating_max) if self.zinc_coating_max is not None else None,
            "zinc_coating_max_operator": self.zinc_coating_max_operator,
            # 加减价
            "price_adjustment": self.price_adjustment,
            "is_base": 1 if self.is_base else 0,
            "sort_order": self.sort_order,
            # Excel 原始位置
            "excel_row": self.excel_row,
            "excel_col": self.excel_col,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
