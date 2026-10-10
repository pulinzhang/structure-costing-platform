"""阶梯项模型。

表示一个厚度+宽度区间对应的加减价。
当某一维度字段全部为 None 时，该维度不参与匹配限制。
例如: 厚度 >= 1.0 < 1.2, 宽度 >= 900 < 1600 → 加价 +100 元/吨
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict


class ParsedLadderItemDump(TypedDict):
    target_sub_group: str | None
    thick_min: float | None
    thick_min_operator: str | None
    thick_max: float | None
    thick_max_operator: str | None
    width_min: float | None
    width_min_operator: str | None
    width_max: float | None
    width_max_operator: str | None
    zinc_coating_min: float | None
    zinc_coating_min_operator: str | None
    zinc_coating_max: float | None
    zinc_coating_max_operator: str | None
    price_adjustment: int
    is_base: int
    sort_order: int
    excel_row: int | None
    excel_col: int | None


@dataclass
class ParsedLadderItem:
    """双维度阶梯明细"""

    # 附加分组条件（如按钢种分组）
    target_sub_group: str | None = None

    # 厚度维度
    thick_min: Decimal | None = None
    thick_min_operator: str | None = ">="
    thick_max: Decimal | None = None
    thick_max_operator: str | None = "<"

    # 宽度维度
    width_min: Decimal | None = None
    width_min_operator: str | None = ">="
    width_max: Decimal | None = None
    width_max_operator: str | None = "<"

    # 锌层克重维度（g/m²）
    zinc_coating_min: Decimal | None = None
    zinc_coating_min_operator: str | None = ">="
    zinc_coating_max: Decimal | None = None
    zinc_coating_max_operator: str | None = "<"

    # 加减价
    price_adjustment: int = 0
    is_base: bool = False  # 是否为基准厚度（加价为0）
    sort_order: int = 0

    # Excel 原始位置（用于测试核对）
    excel_row: int | None = None
    excel_col: int | None = None

    def model_dump(self) -> ParsedLadderItemDump:
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
            "zinc_coating_min": float(self.zinc_coating_min)
            if self.zinc_coating_min is not None
            else None,
            "zinc_coating_min_operator": self.zinc_coating_min_operator,
            "zinc_coating_max": float(self.zinc_coating_max)
            if self.zinc_coating_max is not None
            else None,
            "zinc_coating_max_operator": self.zinc_coating_max_operator,
            # 加减价
            "price_adjustment": self.price_adjustment,
            "is_base": 1 if self.is_base else 0,
            "sort_order": self.sort_order,
            # Excel 原始位置
            "excel_row": self.excel_row,
            "excel_col": self.excel_col,
        }

    def to_dict(self) -> ParsedLadderItemDump:
        return self.model_dump()
