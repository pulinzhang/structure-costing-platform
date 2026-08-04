"""单条政策模型。

一条政策 = 一个钢种 + 一类区间（厚度或宽度）+ 多个阶梯项。
例如:
    steel_mill="马钢(新)", category_name="冷轧钢", grade_type="GRADE", grade_value="DC01",
    policy_type="THICKNESS", base_thickness=Decimal("1.0"),
    items=[{min=0.5, >=}, {max=900, <=}, price=100, ...]

grade_type 取值:
    GRADE            - 钢种牌号（如 DC01、DX51D+Z）
    WIDTH_RANGE      - 宽度范围（如 700≤W<900、<1500）
    CATEGORY         - 钢材大类（如 冷轧钢），用于通用宽度加价
    THICKNESS_RANGE  - 厚度范围（如 厚度≤1.5mm），用于按厚度区分的宽度加价
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from .ladder_item import ParsedLadderItem

POLICY_TYPE_THICKNESS = "THICKNESS"
POLICY_TYPE_WIDTH = "WIDTH"
POLICY_TYPE_THICKNESS_WIDTH = "THICKNESS_WIDTH"  # 厚度-宽度组合（如鞍神）
POLICY_TYPE_ZINC_COATING = "ZINC_COATING"  # 锌层加价（如山钢）

GRADE_TYPE_GRADE = "GRADE"
GRADE_TYPE_WIDTH_RANGE = "WIDTH_RANGE"
GRADE_TYPE_CATEGORY = "CATEGORY"
GRADE_TYPE_THICKNESS_RANGE = "THICKNESS_RANGE"
GRADE_TYPE_THICKNESS_COND = "THICKNESS_COND"  # 厚度条件（≥0.6mm / <0.6mm）


@dataclass
class ParsedPolicy:
    steel_mill: str
    category_name: str
    grade_type: str
    grade_value: str
    policy_type: str
    base_thickness: Optional[Decimal] = None
    items: List[ParsedLadderItem] = field(default_factory=list)

    def model_dump(self) -> dict:
        """返回字典格式，兼容 Pydantic 接口"""
        return {
            "steel_mill": self.steel_mill,
            "category_name": self.category_name,
            "grade_type": self.grade_type,
            "grade_value": self.grade_value,
            "policy_type": self.policy_type,
            "base_thickness": float(self.base_thickness) if self.base_thickness is not None else None,
            "items": [item.to_dict() for item in self.items],
        }

    def to_dict(self) -> dict:
        return self.model_dump()
