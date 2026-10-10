"""基准价解析的中间类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import NotRequired, TypedDict


class BasePriceRecord(TypedDict):
    """一行基准价。解析器写入的键必填；导入会读、解析器不写的 remark 可选。"""

    location: str
    steel_mill: str
    category_name: str
    grade: str
    spec: str
    thick: Decimal | None
    width: Decimal | None
    base_price: Decimal
    processing_fee: Decimal
    sheet_name: str
    excel_row: int
    excel_col: int
    remark: NotRequired[str]


@dataclass
class BaseColumnConfig:
    """一座已命中 lookup 的基地列对。mill_col 为 None 表示仅价格列（钢厂在附页或承接）。"""

    location: str
    mill_col: int | None
    price_col: int


@dataclass
class ParsedContext:
    """一张定价表解析时的列位。"""

    base_configs: list[BaseColumnConfig]
    spec_col: int
    sheet_name: str
    sheet_grade_mills: dict[str, str] | None = None
    carry_mills: dict[tuple[str, str], str] | None = None


@dataclass
class ParseResult:
    """解析结果。"""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    records: list[BasePriceRecord] = field(default_factory=list)
