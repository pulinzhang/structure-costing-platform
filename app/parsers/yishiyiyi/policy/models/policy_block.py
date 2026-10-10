"""厚度块和宽度块共用的定位结果。

定位器写出的键是必填。只在读取处出现、定位器不一定写的键是可选。
"""

from __future__ import annotations

from decimal import Decimal
from typing import NotRequired, TypedDict


class WidthRange(TypedDict, total=False):
    """VAMA 读取的宽度范围。当前定位器不写这个键。"""

    min_val: Decimal | None
    min_operator: str
    max_val: Decimal | None
    max_operator: str


class PolicyBlock(TypedDict):
    category_name: str
    policy_type: str
    grade_col: int
    header_row: int
    price_cols: list[int]
    data_row_start: int
    data_row_end: int
    base_thickness: Decimal | None
    grade_blacklist: NotRequired[frozenset[str]]
    width_range: NotRequired[WidthRange]
