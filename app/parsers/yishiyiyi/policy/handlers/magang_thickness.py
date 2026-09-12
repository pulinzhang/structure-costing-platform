"""马钢厚度解析：写死厚度范围表，以及默认厚度块装配。"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.handlers.base_handler.base_handler import BaseSheetHandler

# 厚度范围写死（用户确认，每月只有价格变化，格式固定）
# (row -> (thick_min, thick_min_op, thick_max, thick_max_op))
_THICKNESS_RANGE_MAP = {
    # Block 1: 冷轧钢宽度加减价
    4: (None, ">=", Decimal("2.5"), "<"),  # 厚度＜2.5
    5: (Decimal("2.5"), ">=", None, "<"),  # 厚度≥2.5
    # Block 2: 冷轧卷板（非高强）
    10: (None, ">=", Decimal("0.8"), "<"),  # 厚度＜0.8
    11: (Decimal("0.8"), ">=", None, "<"),  # 厚度≥0.8
    # Block 3: 冷轧卷板（高强）
    14: (Decimal("0.3"), ">=", Decimal("3.0"), "<="),  # 0.3～3.0
    # Block 4: 镀锌卷板（非高强）
    23: (Decimal("0.3"), ">=", Decimal("2.5"), "<="),  # 0.3～2.5
    # Block 5: 镀锌卷板（高强）
    27: (Decimal("0.3"), ">=", Decimal("2.5"), "<="),  # 0.3～2.5
    # Block 6: 镀锌卷板（高强）
    30: (Decimal("0.3"), ">=", Decimal("2.5"), "<="),  # 0.3～2.5
}


def _parse_thickness_label(label: str) -> tuple[float | None, str, float | None, str]:
    """解析厚度范围标签。
    支持：厚度<0.8 | 厚度≥0.8 | 0.3～3.0（闭区间）
    """
    if not label:
        return None, ">=", None, "<"

    label = label.strip()

    # 闭区间：0.3～3.0 → 0.3 <= t <= 3.0
    m = re.match(r"^([\d.]+)\s*[～~]\s*([\d.]+)$", label)
    if m:
        return float(m.group(1)), ">=", float(m.group(2)), "<="

    # 厚度<0.8
    m = re.match(r"^厚度\s*[＜<]\s*([\d.]+)$", label)
    if m:
        return None, ">=", float(m.group(1)), "<"

    # 厚度≥0.8
    m = re.match(r"^厚度\s*[≥>=]+\s*([\d.]+)$", label)
    if m:
        return float(m.group(1)), ">=", None, "<"

    return None, ">=", None, "<"


def parse_thickness_fixed(
    handler: BaseSheetHandler, sheet: Worksheet, steel_mill: str
) -> list[Any]:
    """复用默认厚度块定位，再交给 PolicyAssembler 装配。"""
    blocks = handler.find_default_thickness_blocks(sheet, steel_mill)
    policies: list[Any] = []
    for block in blocks:
        policies.extend(handler.assembler.build_policies_from_block(sheet, steel_mill, block))
    return policies
