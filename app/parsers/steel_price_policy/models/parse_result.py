"""解析结果聚合。"""

from dataclasses import dataclass, field
from typing import List

from .policy import ParsedPolicy


@dataclass
class SteelPricePolicyParseResult:
    """一张钢价政策表解析的最终结果。"""

    policies: List[ParsedPolicy] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sheet_names: List[str] = field(default_factory=list)
    year: int = 0
    month: int = 0

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "month": self.month,
            "sheet_names": self.sheet_names,
            "policies": [p.to_dict() for p in self.policies],
            "warnings": list(self.warnings),
        }
