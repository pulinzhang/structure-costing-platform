"""解析结果聚合。"""

from dataclasses import dataclass, field
from typing import TypedDict

from .policy import ParsedPolicy, ParsedPolicyDump


class SteelPricePolicyParseResultDump(TypedDict):
    year: int
    month: int
    sheet_names: list[str]
    policies: list[ParsedPolicyDump]
    warnings: list[str]


@dataclass
class SteelPricePolicyParseResult:
    """一张钢价政策表解析的最终结果。"""

    policies: list[ParsedPolicy] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sheet_names: list[str] = field(default_factory=list)
    year: int = 0
    month: int = 0

    def to_dict(self) -> SteelPricePolicyParseResultDump:
        return {
            "year": self.year,
            "month": self.month,
            "sheet_names": self.sheet_names,
            "policies": [p.to_dict() for p in self.policies],
            "warnings": list(self.warnings),
        }
