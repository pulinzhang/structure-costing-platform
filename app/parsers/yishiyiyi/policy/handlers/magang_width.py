"""马钢宽度加减价：固定区域 N2:T30、列头边界与行内阶梯项。"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.models.ladder_item import ParsedLadderItem
from app.parsers.yishiyiyi.policy.models.policy import (
    GRADE_TYPE_THICKNESS_RANGE,
    POLICY_TYPE_WIDTH,
    ParsedPolicy,
)
from app.parsers.yishiyiyi.policy.value_parser import _to_int_price

from .magang_thickness import _THICKNESS_RANGE_MAP

# 马钢历史数据中使用的宽度边界格式 → (min_val, min_op, max_val, max_op)
# 这些格式是写死的，因为马钢历史数据格式固定不变
_WIDTH_BOUNDARY_MAP = {
    "＜900": (None, ">=", Decimal("900"), "<"),
    "＜1000": (None, ">=", Decimal("1000"), "<"),
    "1000≤宽度≤1250": (Decimal("1000"), ">=", Decimal("1250"), "<="),
    "1000≤宽度≤1350": (Decimal("1000"), ">=", Decimal("1350"), "<="),
    "1000≤宽度＜1200": (Decimal("1000"), ">=", Decimal("1200"), "<"),
    "1000≤宽度＜1400": (Decimal("1000"), ">=", Decimal("1400"), "<"),
    "1200≤宽度＜1650": (Decimal("1200"), ">=", Decimal("1650"), "<"),
    "1250＜宽度≤1500": (Decimal("1250"), ">", Decimal("1500"), "<="),
    "1350＜宽度≤1650": (Decimal("1350"), ">", Decimal("1650"), "<="),
    "1400≤宽度＜1500": (Decimal("1400"), ">=", Decimal("1500"), "<"),
    "1500＜宽度≤1680": (Decimal("1500"), ">", Decimal("1680"), "<="),
    "1650＜宽度＜1850": (Decimal("1650"), ">", Decimal("1850"), "<"),
    "900≤宽度＜1000": (Decimal("900"), ">=", Decimal("1000"), "<"),
    "≥1500": (Decimal("1500"), ">=", None, "<"),
    "≥1650": (Decimal("1650"), ">=", None, "<"),
    "≥1850": (Decimal("1850"), ">=", None, "<"),
    "≥1900": (Decimal("1900"), ">=", None, "<"),
}

_UPPER_BOUND_RE = re.compile(r"^[＜<=]\s*(\d+)$")


def _parse_width_boundary(text: str) -> tuple[Decimal | None, str, Decimal | None, str]:
    """解析宽度边界，返回 (min_val, min_op, max_val, max_op)

    马钢历史数据格式固定，直接查表返回。
    """
    if not text:
        return None, ">=", None, "<"

    text = str(text).strip()

    # 先尝试精确匹配
    if text in _WIDTH_BOUNDARY_MAP:
        return _WIDTH_BOUNDARY_MAP[text]

    # 纯数字结尾的上界（兜底，如 "＜850" 这种未知的上界格式）
    m = _UPPER_BOUND_RE.match(text)
    if m:
        return None, ">=", Decimal(m.group(1)), "<"

    # 兜底
    return None, ">=", None, "<"


def _infer_width_boundaries(
    raw: dict[int, tuple[Decimal | None, str, Decimal | None, str]],
    price_cols: list[int],
) -> dict[int, tuple[Decimal | None, str, Decimal | None, str]]:
    """推断完整边界：补全 min/max 为 None 的列"""
    result: dict[int, tuple[Decimal | None, str, Decimal | None, str]] = {}
    sorted_cols = sorted(price_cols)

    for i, c in enumerate(sorted_cols):
        if c not in raw:
            continue

        min_val, min_op, max_val, max_op = raw[c]

        # 推断下界
        if min_val is None:
            if i == 0:
                min_val = Decimal("0")
                min_op = ">="
            else:
                prev_c = sorted_cols[i - 1]
                if prev_c in raw:
                    _, _, prev_max, prev_max_op = raw[prev_c]
                    if prev_max is not None:
                        min_val = prev_max
                        min_op = ">" if prev_max_op == "<=" else ">="

        # 推断上界
        if max_val is None and i < len(sorted_cols) - 1:
            next_c = sorted_cols[i + 1]
            if next_c in raw:
                next_min, next_min_op, _, _ = raw[next_c]
                if next_min is not None:
                    max_val = next_min
                    # 如果下一列的下界是严格大于(>)，则推断的上界是严格小于(<)
                    # 否则保持当前列的上界操作符
                    max_op = "<" if next_min_op == ">" else max_op

        result[c] = (min_val, min_op, max_val, max_op)

    return result


def _parse_width_boundary_cold_high_strength(
    price_cols: list[int],
) -> dict[int, tuple[Decimal | None, str, Decimal | None, str]]:
    """冷轧卷板（高强）特殊宽度边界：列头文本 <900 <1000 ... 与实际含义不符。

    实际映射（固定写死）：
        col15 <900        → w < 900
        col16 <1000       → 900 <= w < 1000   （<1000 实际是第二段）
        col17 1000≤w<1400 → 1000 <= w < 1400
        col18 1400≤w<1500 → 1400 <= w < 1500
        col19 ≥1500       → w >= 1500
    """
    result: dict[int, tuple[Decimal | None, str, Decimal | None, str]] = {}

    # col15: w < 900
    if 15 in price_cols:
        result[15] = (None, ">=", Decimal("900"), "<")

    # col16: 900 <= w < 1000
    if 16 in price_cols:
        result[16] = (Decimal("900"), ">=", Decimal("1000"), "<")

    # col17: 1000 <= w < 1400
    if 17 in price_cols:
        result[17] = (Decimal("1000"), ">=", Decimal("1400"), "<")

    # col18: 1400 <= w < 1500
    if 18 in price_cols:
        result[18] = (Decimal("1400"), ">=", Decimal("1500"), "<")

    # col19: w >= 1500
    if 19 in price_cols:
        result[19] = (Decimal("1500"), ">=", None, "<")

    return result


# 冷轧非高强钢种
_COLD_ROLL_NORMAL_GRADES = [
    "DC01",
    "DC03",
    "DC04",
    "DC06",
    "B180H1",
    "B170P1/HC180Y",
    "B210P1/HC220Y",
    "B250P1/HC260Y",
    "HC340/590DP",
    "HC340LA",
    "HC420LA",
    "HC420/780DP",
]

# 高强冷轧钢种
_COLD_ROLL_HIGH_STRENGTH_GRADES = [
    "QSTE420TM",
    "SAPH370",
    "SAPH440",
    "SPHC",
    "SPHE",
]

# 镀锌非高强钢种
_GALVANIZED_NORMAL_GRADES = [
    "DC54D+Z",
    "DC56D+Z",
    "HC180YD+Z",
    "HC220YD+Z",
    "HC260YD+Z",
    "HC340/590DPD+Z",
    "HC420/780DPD+Z",
    "HC340LAD+Z",
    "HC420LAD+Z",
    "HC500LAD+Z",
]

# 镀锌高强钢种1：H300LA及以上低合金、HC250/450DPD及以上双相钢、HC380/590TRD及以上
_GALVANIZED_HIGH_STRENGTH_GRADES_1 = [
    "H300LA",
    "HC250/450DPD",
    "HC380/590TRD",
    "HC300/500DPD",
    "HC340/600DPD",
    "HC380/600DPD",
    "HC420/780TRD",
    "HC460/780TRD",
    "HC500/780TRD",
]

# 镀锌高强钢种2：CR240LA、H260YD、H260LAD、H260PD、M260LYD
_GALVANIZED_HIGH_STRENGTH_GRADES_2 = [
    "CR240LA",
    "H260YD",
    "H260LAD",
    "H260PD",
    "M260LYD",
]


class _WidthRegion:
    def __init__(
        self,
        title: str,
        category: str,
        grade_value_fn: Any,
        header_row: int,
        price_col_start: int,
        price_col_end: int,
        data_row_start: int,
        data_row_end: int,
        grades: list[str] | None = None,
    ):
        self.title = title
        self.category = category
        self.grade_value_fn = grade_value_fn
        self.header_row = header_row
        self.price_col_start = price_col_start
        self.price_col_end = price_col_end
        self.data_row_start = data_row_start
        self.data_row_end = data_row_end
        self.grades = grades or []


def _grade_from_col14(sheet: Worksheet, row: int) -> str | None:
    v = sheet.cell(row=row, column=14).value
    return str(v).strip() if v is not None else None


def _grade_from_col15(sheet: Worksheet, row: int) -> str | None:
    v = sheet.cell(row=row, column=15).value
    if v is not None:
        return str(v).strip()
    for mr in range(row, 0, -1):
        cv = sheet.cell(row=mr, column=15).value
        if cv is not None:
            return str(cv).strip()
        if mr < row:
            break
    return None


# 六个固定区域
_WIDTH_REGIONS: list[_WidthRegion] = [
    # 1. 冷轧钢宽度加减价
    _WidthRegion(
        title="冷轧钢宽度加减价",
        category="冷轧钢",
        grade_value_fn=_grade_from_col14,
        header_row=3,
        price_col_start=15,
        price_col_end=18,
        data_row_start=4,
        data_row_end=5,
        grades=[],  # 通用冷轧钢宽度加减价
    ),
    # 2. 冷轧卷板（非高强）
    _WidthRegion(
        title="冷轧卷板（非高强）",
        category="冷轧卷板（非高强）",
        grade_value_fn=_grade_from_col14,
        header_row=9,
        price_col_start=15,
        price_col_end=20,
        data_row_start=10,
        data_row_end=11,
        grades=_COLD_ROLL_NORMAL_GRADES,
    ),
    # 3. 高强冷轧卷宽度加减价
    _WidthRegion(
        title="冷轧卷板（高强）",
        category="冷轧卷板（高强）",
        grade_value_fn=_grade_from_col15,
        header_row=13,
        price_col_start=15,
        price_col_end=19,
        data_row_start=14,
        data_row_end=14,
        grades=_COLD_ROLL_HIGH_STRENGTH_GRADES,
    ),
    # 4. 镀锌卷板（非高强）
    _WidthRegion(
        title="镀锌卷板（非高强）",
        category="镀锌卷板（非高强）",
        grade_value_fn=_grade_from_col15,
        header_row=22,
        price_col_start=15,
        price_col_end=19,
        data_row_start=23,
        data_row_end=23,
        grades=_GALVANIZED_NORMAL_GRADES,
    ),
    # 5. 镀锌卷板（高强）
    _WidthRegion(
        title="镀锌卷板（高强）",
        category="镀锌卷板（高强）",
        grade_value_fn=_grade_from_col15,
        header_row=26,
        price_col_start=15,
        price_col_end=19,
        data_row_start=27,
        data_row_end=27,
        grades=_GALVANIZED_HIGH_STRENGTH_GRADES_1,
    ),
    # 6. 镀锌卷板（高强）
    _WidthRegion(
        title="镀锌卷板（高强）",
        category="镀锌卷板（高强）",
        grade_value_fn=_grade_from_col15,
        header_row=29,
        price_col_start=15,
        price_col_end=19,
        data_row_start=30,
        data_row_end=30,
        grades=_GALVANIZED_HIGH_STRENGTH_GRADES_2,
    ),
]


def parse_width_fixed(sheet: Worksheet, steel_mill: str, warnings: list[str]) -> list[Any]:
    """六个固定宽度区域逐块解析。"""
    policies: list[Any] = []
    for region in _WIDTH_REGIONS:
        policies.extend(parse_one_region(sheet, steel_mill, region, warnings))
    return policies


def parse_one_region(
    sheet: Worksheet,
    steel_mill: str,
    region: _WidthRegion,
    warnings: list[str],
) -> list[Any]:
    """分两步处理：
    对于grades为空的，说明是冷轧卷类
    对于grades不为空的，说明是板类。grades里的每一个都是一个policy
    也就是对应主表里的，grade_value
    """
    header_row = region.header_row
    price_cols = list(range(region.price_col_start, region.price_col_end + 1))
    data_start = region.data_row_start
    data_end = region.data_row_end

    # Step 1: 宽引入 - 收集所有钢种行
    grade_rows_with_value = []
    for r in range(data_start, data_end + 1):
        grade_value = region.grade_value_fn(sheet, r)
        if not grade_value:
            continue
        grade_rows_with_value.append((r, grade_value))

    if not grade_rows_with_value:
        warnings.append(f"[{region.title}] 未找到钢种行，跳过")
        return []

    # Step 2: 宽度块处理 - 解析列头宽度边界
    raw_boundaries: dict[int, tuple[Decimal | None, str, Decimal | None, str]] = {}
    for c in price_cols:
        cell_text = sheet.cell(row=header_row, column=c).value
        if cell_text is not None:
            raw_boundaries[c] = _parse_width_boundary(str(cell_text))

    if not raw_boundaries:
        warnings.append(f"[{region.title}] 列头行 {header_row} 未找到宽度边界，跳过")
        return []

    boundaries = _infer_width_boundaries(raw_boundaries, price_cols)
    if not boundaries:
        return []

    # Step 3/4: 构建 policy
    # grades 不为空 -> 板类：使用 region.grades；为空 -> 冷轧卷类：用行内 grade_value
    policies: list[Any] = []
    if region.grades:
        # 板类：外层是行（每行代表一个厚度范围），里层是该行对应的钢种；
        # 同一行的价格数据被所有钢种共用
        for data_row, _ in grade_rows_with_value:
            for grade_value in region.grades:
                items = build_width_items(sheet, data_row, price_cols, boundaries)
                if not items:
                    continue
                # Block 2: 行 10 → 厚度<0.8，行 11 → 厚度≥0.8
                if data_row in (10, 11):
                    thick_range_label = "厚度<0.8" if data_row == 10 else "厚度≥0.8"
                    category_name = region.category + thick_range_label
                else:
                    category_name = region.category
                policies.append(
                    ParsedPolicy(
                        steel_mill=steel_mill,
                        category_name=category_name,
                        grade_type=GRADE_TYPE_THICKNESS_RANGE,
                        grade_value=grade_value,
                        policy_type=POLICY_TYPE_WIDTH,
                        base_thickness=None,
                        items=items,
                    )
                )
    else:
        # 冷轧卷类：使用行数据中的 grade_value
        for r, grade_value in grade_rows_with_value:
            items = build_width_items(sheet, r, price_cols, boundaries)
            if not items:
                continue
            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=region.category,
                    grade_type=GRADE_TYPE_THICKNESS_RANGE,
                    grade_value=grade_value,
                    policy_type=POLICY_TYPE_WIDTH,
                    base_thickness=None,
                    items=items,
                )
            )

    return policies


def build_width_items(
    sheet: Worksheet,
    row: int,
    price_cols: list[int],
    boundaries: dict[int, tuple[Decimal | None, str, Decimal | None, str]],
) -> list[ParsedLadderItem]:
    """构建某行的宽度阶梯 items（厚度范围从写死的 _THICKNESS_RANGE_MAP 获取）"""
    # 从写死的厚度范围表获取
    thick_min, thick_min_op, thick_max, thick_max_op = _THICKNESS_RANGE_MAP.get(
        row, (None, ">=", None, "<")
    )

    items: list[ParsedLadderItem] = []
    sorted_cols = sorted(price_cols)

    for i, c in enumerate(sorted_cols):
        if c not in boundaries:
            continue

        min_val, min_op, max_val, max_op = boundaries[c]
        price = _to_int_price(sheet.cell(row=row, column=c).value)

        if price == 0 and min_val is None and max_val is None:
            continue

        items.append(
            ParsedLadderItem(
                target_sub_group=None,
                thick_min=thick_min,
                thick_min_operator=thick_min_op,
                thick_max=thick_max,
                thick_max_operator=thick_max_op,
                width_min=min_val,
                width_min_operator=min_op,
                width_max=max_val,
                width_max_operator=max_op,
                price_adjustment=price,
                is_base=False,
                sort_order=row * 100 + i,
                excel_row=row,
                excel_col=c,
            )
        )

    return items
