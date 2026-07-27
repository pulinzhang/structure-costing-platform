"""单条政策模型。

一条政策 = 一个钢种 + 一类区间（厚度或宽度）+ 多个阶梯项。
例如:
    steel_mill="马钢(新)", category_name="冷轧钢", grade_name="DC01",
    policy_type="THICKNESS", base_thickness=Decimal("1.0"),
    items=[{min=0.5, >=}, {max=900, <=}, price=100, ...]
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from .ladder_item import ParsedLadderItem

POLICY_TYPE_THICKNESS = "THICKNESS"
POLICY_TYPE_WIDTH = "WIDTH"


@dataclass
class ParsedPolicy:
    steel_mill: str
    category_name: str
    grade_name: str
    policy_type: str
    base_thickness: Optional[Decimal] = None
    items: List[ParsedLadderItem] = field(default_factory=list)

    def model_dump(self) -> dict:
        """返回字典格式，兼容 Pydantic 接口"""
        return {
            "steel_mill": self.steel_mill,
            "category_name": self.category_name,
            "grade_name": self.grade_name,
            "policy_type": self.policy_type,
            "base_thickness": float(self.base_thickness) if self.base_thickness is not None else None,
            "items": [item.to_dict() for item in self.items],
        }

    def to_dict(self) -> dict:
        return self.model_dump()
