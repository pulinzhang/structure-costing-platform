"""阶梯项模型。

表示一个厚度区间或宽度区间对应的加减价。
例如: 厚度 >= 1.0 <= 1.2 → 加价 +100 元/吨
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class ParsedLadderItem:
    min_val: Optional[Decimal] = None
    min_operator: Optional[str] = None
    max_val: Optional[Decimal] = None
    max_operator: Optional[str] = None
    price_adjustment: int = 0
    is_base: bool = False  # 是否为基准厚度（加价为0）

    @property
    def is_open_upper(self) -> bool:
        """上限开放（无 max_val）。"""
        return self.max_val is None

    @property
    def is_open_lower(self) -> bool:
        """下限开放（无 min_val）。"""
        return self.min_val is None

    def model_dump(self) -> dict:
        """返回字典格式，兼容 Pydantic 接口"""
        return {
            "min_val": float(self.min_val) if self.min_val is not None else None,
            "min_operator": self.min_operator,
            "max_val": float(self.max_val) if self.max_val is not None else None,
            "max_operator": self.max_operator,
            "price_adjustment": self.price_adjustment,
            "is_base": self.is_base,
        }

    def to_dict(self) -> dict:
        return self.model_dump()
