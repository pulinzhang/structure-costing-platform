"""基准价解析的中间类型。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaseColumnConfig:
    """一座已命中 lookup 的基地列对。"""

    location: str
    mill_col: int
    price_col: int


@dataclass
class ParsedContext:
    """一张定价表解析时的列位。"""

    base_configs: list[BaseColumnConfig]
    spec_col: int
    sheet_name: str


@dataclass
class ParseResult:
    """解析结果。"""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
