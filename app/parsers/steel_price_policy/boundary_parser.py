"""列头区间描述解析。

将以下类型的列头解析为 _Boundary:
- "≥0.5"        → min=0.5, op=">=" （下限）
- "≤950mm"      → max=950, op="<=" （上限，全宽 ≤）
- "＜1000"      → max=1000, op="<"  （上限，全宽 <）
- "＞950mm"     → min=950, op=">"  （下限，全宽 >）
- "1000≤W≤1600" → min=1000, op=">=", max=1600, op="<="
- "1000≤宽＜1600" → min=1000, op=">=", max=1600, op="<" （≤宽＜：上限不含）
- "900＜W＜1000" → min=900, op=">", max=1000, op="<"   （新增支持）
- "1000-T<1600" → min=1000, op=">",  max=1600, op="<="
- "1000-1600"   → min=1000, op=">=", max=1600, op="<="
- "1000-1600mm" → min=1000, op=">=", max=1600, op="<="

注意：
- 全角/半角符号同时支持：≥/＞, ≤/＜, </> 都识别
- 当 <= 形式使用 ≤/＜= 时返回 op="<="；
  使用普通 < 时返回 op="<"
- 单位 "mm" / "W" / "T" / "t" / "w" 后缀会自动忽略
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from .value_parser import _to_str


# ===========================================================================
# 1. 正则表达式定义（按优先级分组）
# ===========================================================================

# ---------- 1.1 纯数字（无符号，可选mm单位）→ min=max ----------
_PATTERN_PURE_NUM = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(?:mm)?\s*$", re.IGNORECASE)

# ---------- 1.2 单边符号 ----------
_PATTERN_GT = re.compile(r"^[>＞](?!=)\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$")   # >0.5 / ＞0.5
_PATTERN_GTE = re.compile(r"^(?:[≥]|>=)\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$") # ≥0.5 / >=0.5
_PATTERN_LTE = re.compile(r"^[≤<＜]=?\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$")   # ≤800 / <=800 / ＜1000

# ---------- 1.3 简单区间（不含变量） ----------
_PATTERN_SIMPLE_RANGE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[-~]\s*(-?\d+(?:\.\d+)?)\s*$"
)
_PATTERN_SIMPLE_RANGE_WITH_UNIT = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[-~]\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*\s*$"
)

# ---------- 1.3 VAMA 特殊 "≥X-Y" 格式（显式给定上下界，终结档） ----------
# 格式：≥2.0-2.3 → min=2.0 (>=), max=2.3 (<=)
# 注意：必须放在简单区间之前，因为 ≥ 前缀会干扰普通 X-Y 匹配
_PATTERN_GTE_RANGE = re.compile(
    r"^\s*(?:≥|>=\s*)\s*(-?\d+(?:\.\d+)?)\s*[-–—]\s*(-?\d+(?:\.\d+)?)\s*$"
)

# ---------- 1.4 特殊 "1000-T<1600" 格式 ----------
# 注意：此处变量为 T/t，不是 W/宽，需保留原有逻辑
_PATTERN_GTE_LT_RANGE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[≥>＞]=?\s*[Tt]?\s*<\s*(-?\d+(?:\.\d+)?)\s*$"
)

# ---------- 1.5 四种 W 区间（必须严格区分，按顺序匹配） ----------
# 全角/半角兼容：
#   - 严格小于: [<＜]
#   - 小于等于: (?:<=|≤|＜=)
#   - 变量名: [Ww宽]
# 每个正则末尾带 \s*[a-zA-Z]* 忽略单位

# (a) X < W < Y  （下限严格 >，上限严格 <）
_PATTERN_W_STRICT_BOTH = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[<＜]\s*[Ww宽]\s*[<＜]\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$"
)

# (b) X <= W < Y （下限 >=，上限严格 <）
_PATTERN_W_LEFT_INC_RIGHT_STRICT = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*(?:<=|≤|＜=)\s*[Ww宽]\s*[<＜]\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$"
)

# (c) X < W <= Y （下限严格 >，上限 <=）
_PATTERN_W_LEFT_STRICT_RIGHT_INC = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[<＜]\s*[Ww宽]\s*(?:<=|≤|＜=)\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$"
)

# (d) X <= W <= Y （下限 >=，上限 <=）
_PATTERN_W_INC_BOTH = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*(?:<=|≤|＜=)\s*[Ww宽]\s*(?:<=|≤|＜=)\s*(-?\d+(?:\.\d+)?)\s*[a-zA-Z]*$"
)

# ===========================================================================
# 2. 数据结构
# ===========================================================================
@dataclass
class _Boundary:
    min_val: Optional[Decimal] = None
    min_operator: Optional[str] = None
    max_val: Optional[Decimal] = None
    max_operator: Optional[str] = None


# ===========================================================================
# 3. 解析函数（按优先级顺序匹配）
# ===========================================================================
def _parse_boundary(header: Any) -> Optional[_Boundary]:
    """解析列头为区间描述。"""
    text = _to_str(header)
    if not text:
        return None

    # ---------- 优先级1：四种 W 区间（按严格程度降序） ----------
    # 1a) X < W < Y  → min=">", max="<"
    match = _PATTERN_W_STRICT_BOTH.match(text)
    if match:
        lo, hi = Decimal(match.group(1)), Decimal(match.group(2))
        return _Boundary(min_val=lo, min_operator=">", max_val=hi, max_operator="<")

    # 1b) X <= W < Y → min=">=", max="<"
    match = _PATTERN_W_LEFT_INC_RIGHT_STRICT.match(text)
    if match:
        lo, hi = Decimal(match.group(1)), Decimal(match.group(2))
        return _Boundary(min_val=lo, min_operator=">=", max_val=hi, max_operator="<")

    # 1c) X < W <= Y → min=">", max="<="
    match = _PATTERN_W_LEFT_STRICT_RIGHT_INC.match(text)
    if match:
        lo, hi = Decimal(match.group(1)), Decimal(match.group(2))
        return _Boundary(min_val=lo, min_operator=">", max_val=hi, max_operator="<=")

    # 1d) X <= W <= Y → min=">=", max="<="
    match = _PATTERN_W_INC_BOTH.match(text)
    if match:
        lo, hi = Decimal(match.group(1)), Decimal(match.group(2))
        return _Boundary(min_val=lo, min_operator=">=", max_val=hi, max_operator="<=")

    # ---------- 优先级2：特殊 "1000-T<1600" ----------
    match_gtlt = _PATTERN_GTE_LT_RANGE.match(text)
    if match_gtlt:
        lo, hi = Decimal(match_gtlt.group(1)), Decimal(match_gtlt.group(2))
        return _Boundary(min_val=lo, min_operator=">", max_val=hi, max_operator="<=")

    # ---------- 优先级3：VAMA 特殊 ≥X-Y（终结档） ----------
    match_gte_range = _PATTERN_GTE_RANGE.match(text)
    if match_gte_range:
        lo = Decimal(match_gte_range.group(1))
        hi = Decimal(match_gte_range.group(2))
        return _Boundary(min_val=lo, min_operator=">=", max_val=hi, max_operator="<=")

    # ---------- 优先级3：简单区间（带单位或不带） ----------
    match_simple_unit = _PATTERN_SIMPLE_RANGE_WITH_UNIT.match(text)
    if match_simple_unit:
        lo, hi = Decimal(match_simple_unit.group(1)), Decimal(match_simple_unit.group(2))
        return _Boundary(min_val=lo, min_operator=">=", max_val=hi, max_operator="<=")

    match_simple = _PATTERN_SIMPLE_RANGE.match(text)
    if match_simple:
        lo, hi = Decimal(match_simple.group(1)), Decimal(match_simple.group(2))
        return _Boundary(min_val=lo, min_operator=">=", max_val=hi, max_operator="<=")

    # ---------- 优先级4：单边大于 / 大于等于 ----------
    match_gt = _PATTERN_GT.match(text)
    if match_gt:
        return _Boundary(min_val=Decimal(match_gt.group(1)), min_operator=">")

    match_gte = _PATTERN_GTE.match(text)
    if match_gte:
        return _Boundary(min_val=Decimal(match_gte.group(1)), min_operator=">=")

    # ---------- 优先级5：单边小于 / 小于等于 ----------
    match_lte = _PATTERN_LTE.match(text)
    if match_lte:
        raw = text.strip()
        # 根据首部符号判断操作符
        if raw.startswith(("≤", "<=", "＜=")):
            op = "<="
        else:  # 以 "<" 或 "＜" 开头
            op = "<"
        return _Boundary(max_val=Decimal(match_lte.group(1)), max_operator=op)

    # ---------- 优先级6：纯数字（无符号）→ min=max ----------
    match_pure = _PATTERN_PURE_NUM.match(text)
    if match_pure:
        val = Decimal(match_pure.group(1))
        return _Boundary(min_val=val, min_operator=">=", max_val=val, max_operator="<=")

    return None


def _parse_boundary_thickness(text: str) -> Optional[_Boundary]:
    """
    厚度专用的 boundary 解析，纯数字视为 "<=x"（无 min 边界）。
    """
    if not text:
        return None

    text = str(text).strip()

    # ---------- >= 区间 ----------
    match_gte = _PATTERN_GTE.match(text)
    if match_gte:
        return _Boundary(min_val=Decimal(match_gte.group(1)), min_operator=">=")

    # ---------- <= 区间 ----------
    match_lte = _PATTERN_LTE.match(text)
    if match_lte:
        raw = text.strip()
        if raw.startswith(("≤", "<=", "＜=")):
            op = "<="
        else:
            op = "<"
        return _Boundary(max_val=Decimal(match_lte.group(1)), max_operator=op)

    # ---------- 纯数字（无符号）→ 仅 max <= ----------
    match_pure = _PATTERN_PURE_NUM.match(text)
    if match_pure:
        return _Boundary(max_val=Decimal(match_pure.group(1)), max_operator="<=")

    return None