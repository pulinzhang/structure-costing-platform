"""列头区间描述解析。

将以下类型的列头解析为 _Boundary:
- "≥0.5"        → min=0.5, op=">=" （下限）
- "≤950mm"      → max=950, op="<=" （上限，全宽 ≤）
- "＜1000"      → max=1000, op="<"  （上限，全宽 <）
- "＞950mm"     → min=950, op=">"  （下限，全宽 >）
- "1000≤W≤1600" → min=1000, op=">=", max=1600, op="<="
- "1000≤宽＜1600" → min=1000, op=">=", max=1600, op="<" （≤宽＜：上限不含）
- "1000-T<1600" → min=1000, op=">",  max=1600, op="<="
- "1000-1600"   → min=1000, op=">=", max=1600, op="<="
- "1000-1600mm" → min=1000, op=">=", max=1600, op="<="

注意：
- 全角/半角符号同时支持：≥/＞, ≤/＜, </> 都识别
- 当 <= 形式使用 ≤/＜ 时返回 op="<="；
  使用普通 < 时返回 op="<"
- 单位 "mm" / "W" / "T" / "t" / "w" 后缀会自动忽略
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from .value_parser import _to_str


# 纯数字（无符号）→ 上限 ≤
_PATTERN_PURE_NUM = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")

# >0.5 / ＞0.5 这两种严格大于（半角 > 和全角 ＞）
_PATTERN_GT = re.compile(r"^[>＞](?!=)\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$")
# ≥0.5 / ≥0.5 这是大于等于
_PATTERN_GTE = re.compile(r"^(?:[≥]|>=)\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$")
_PATTERN_LTE = re.compile(r"^[≤<＜]=?\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$")
_PATTERN_LTE_W_RANGE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[≤<＜]=?\s*[Ww宽]\s*[≤<＜]=?\s*(-?\d+(?:\.\d+)?)\s*$"
)
# X≤宽＜Y：上限不含（op="<"），区分于 X≤W≤Y（op="<="）
_PATTERN_LE_W_RANGE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[≤<＜]=?\s*[Ww宽]\s*<\s*(-?\d+(?:\.\d+)?)\s*$"
)
_PATTERN_GTE_LT_RANGE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[≥>＞]=?\s*[TtWw]?\s*<\s*(-?\d+(?:\.\d+)?)\s*$"
)
_PATTERN_SIMPLE_RANGE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[-~]\s*(-?\d+(?:\.\d+)?)\s*$"
)
_PATTERN_SIMPLE_RANGE_WITH_UNIT = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[-~]\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*\s*$"
)


@dataclass
class _Boundary:
    min_val: Optional[Decimal] = None
    min_operator: Optional[str] = None
    max_val: Optional[Decimal] = None
    max_operator: Optional[str] = None


def _parse_boundary(header: Any) -> Optional[_Boundary]:
    """解析列头为区间描述。"""
    text = _to_str(header)
    if not text:
        return None

    # 1) "1000<=W<=1600" / "1000≤W≤1600"
    match_range = _PATTERN_LTE_W_RANGE.match(text)
    if match_range:
        lo, hi = Decimal(match_range.group(1)), Decimal(match_range.group(2))
        return _Boundary(min_val=lo, min_operator=">=", max_val=hi, max_operator="<=")

    # 1b) "800≤宽＜900" — 上限不含（op="<"）
    match_le_range = _PATTERN_LE_W_RANGE.match(text)
    if match_le_range:
        lo, hi = Decimal(match_le_range.group(1)), Decimal(match_le_range.group(2))
        return _Boundary(min_val=lo, min_operator=">=", max_val=hi, max_operator="<")

    # 2) "1000>=T<1600" / "1000>T<1600"
    match_gtlt = _PATTERN_GTE_LT_RANGE.match(text)
    if match_gtlt:
        lo, hi = Decimal(match_gtlt.group(1)), Decimal(match_gtlt.group(2))
        return _Boundary(min_val=lo, min_operator=">", max_val=hi, max_operator="<=")

    # 3) "1000-1600mm"
    match_simple_unit = _PATTERN_SIMPLE_RANGE_WITH_UNIT.match(text)
    if match_simple_unit:
        lo, hi = Decimal(match_simple_unit.group(1)), Decimal(match_simple_unit.group(2))
        return _Boundary(min_val=lo, min_operator=">=", max_val=hi, max_operator="<=")

    # 4) "1000-1600"
    match_simple = _PATTERN_SIMPLE_RANGE.match(text)
    if match_simple:
        lo, hi = Decimal(match_simple.group(1)), Decimal(match_simple.group(2))
        return _Boundary(min_val=lo, min_operator=">=", max_val=hi, max_operator="<=")

    # 5a) ">0.5" / "＞0.5" 这两种严格大于（半角 > 和全角 ＞）
    match_gt = _PATTERN_GT.match(text)
    if match_gt:
        return _Boundary(min_val=Decimal(match_gt.group(1)), min_operator=">")

    # 5b) "≥0.5" 这是大于等于
    match_gte = _PATTERN_GTE.match(text)
    if match_gte:
        return _Boundary(min_val=Decimal(match_gte.group(1)), min_operator=">=")

    # 6) "≤950mm" / "<950" / "＜950"
    match_lte = _PATTERN_LTE.match(text)
    if match_lte:
        # 半角 "<" 单独出现表示严格小于，">=" 表示小于等于；全角 "≤" / "＜" 总是 <=
        if text.startswith("<=") or text.startswith("＜=") or text.startswith("≤"):
            op = "<="
        else:
            op = "<"
        return _Boundary(max_val=Decimal(match_lte.group(1)), max_operator=op)

    # 7) 纯数字无符号 "0.5" → 上限 ≤（小于等于）
    # 例如宽度表 "950" 可能表示 ≤950，马钢厚度表 "0.5" 表示 ≤0.5
    match_pure = _PATTERN_PURE_NUM.match(text)
    if match_pure:
        return _Boundary(max_val=Decimal(match_pure.group(1)), max_operator="<=")

    return None
