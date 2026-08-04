"""马钢 Sheet 处理器（旧版格式，固定区域 N2:T30）。

六类宽度加减价区域（写死固定行）：
    冷轧钢卷宽度加减价              header_row=3   data_row=4~5    col N(14)-R(18)
    冷轧卷板（非高强）    header_row=9   data_row=10~11  col N(14)-T(20)
    冷轧卷板（高强）      header_row=13  data_row=14      col N(14)-S(19)
    镀锌卷板（非高强）    header_row=22  data_row=23      col N(14)-S(19)
    镀锌卷板（高强）      header_row=26  data_row=27      col N(14)-S(19)
    镀锌卷板（高强）      header_row=29  data_row=30      col N(14)-S(19)

第三类，冷轧卷板（高强）宽度范围是特殊格式：
    列头文本 <900 <1000 1000≤w<1400 1400≤w<1500 ≥1500
    其中"<900"表示 w<900，"<1000"实际是 900≤w<1000，"≥1000"实际是 w≥1000
    因此 col15~col19 的真实边界为：col15(900≤w<1000) col16(w≥1000) col17(1000≤w<1400) col18(1400≤w<1500) col19(w≥1500)

闭区间用"～"表示，如 0.3～3.0 表示 0.3<=t<=3.0
"""

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.steel_price_policy.handlers.base_handler import BaseSheetHandler
from app.parsers.steel_price_policy.models.ladder_item import ParsedLadderItem
from app.parsers.steel_price_policy.models.policy import (
    GRADE_TYPE_THICKNESS_RANGE,
    POLICY_TYPE_WIDTH,
    ParsedPolicy,
)


# ============================================================================
#  六类固定区域定义
# ============================================================================

# 冷轧非高强钢种
_COLD_ROLL_NORMAL_GRADES = [
    "DC01", "DC03", "DC04", "DC06",
    "B180H1", "B170P1/HC180Y", "B210P1/HC220Y", "B250P1/HC260Y",
    "HC340/590DP", "HC340LA", "HC420LA", "HC420/780DP",
]

# 高强冷轧钢种
_COLD_ROLL_HIGH_STRENGTH_GRADES = [
    "QSTE420TM", "SAPH370", "SAPH440", "SPHC", "SPHE",
]

# 镀锌非高强钢种
_GALVANIZED_NORMAL_GRADES = [
    "DC54D+Z", "DC56D+Z",
    "HC180YD+Z", "HC220YD+Z", "HC260YD+Z",
    "HC340/590DPD+Z", "HC420/780DPD+Z",
    "HC340LAD+Z", "HC420LAD+Z", "HC500LAD+Z",
]

# 镀锌高强钢种1：H300LA及以上低合金、HC250/450DPD及以上双相钢、HC380/590TRD及以上
_GALVANIZED_HIGH_STRENGTH_GRADES_1 = [
    "H300LA", "HC250/450DPD", "HC380/590TRD",
    "HC300/500DPD", "HC340/600DPD", "HC380/600DPD",
    "HC420/780TRD", "HC460/780TRD", "HC500/780TRD",
]

# 镀锌高强钢种2：CR240LA、H260YD、H260LAD、H260PD、M260LYD
_GALVANIZED_HIGH_STRENGTH_GRADES_2 = [
    "CR240LA", "H260YD", "H260LAD", "H260PD", "M260LYD",
]


class _WidthRegion:
    def __init__(
        self,
        title: str,
        category: str,
        grade_value_fn: Any,
        header_row: int,
        grade_col: int,
        price_col_start: int,
        price_col_end: int,
        data_row_start: int,
        data_row_end: int,
        grades: Optional[List[str]] = None,
        is_width_special: bool = False,
    ):
        self.title = title
        self.category = category
        self.grade_value_fn = grade_value_fn
        self.header_row = header_row
        self.grade_col = grade_col
        self.price_col_start = price_col_start
        self.price_col_end = price_col_end
        self.data_row_start = data_row_start
        self.data_row_end = data_row_end
        self.grades = grades or []
        self.is_width_special = is_width_special


def _grade_from_col14(sheet: Worksheet, row: int) -> Optional[str]:
    v = sheet.cell(row=row, column=14).value
    return str(v).strip() if v is not None else None


def _grade_from_col15(sheet: Worksheet, row: int) -> Optional[str]:
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
_WIDTH_REGIONS: List[_WidthRegion] = [
    # 1. 冷轧钢宽度加减价  R2:R5  col N(14)-T(20)
    _WidthRegion(
        title="冷轧钢宽度加减价",
        category="冷轧钢",
        grade_value_fn=_grade_from_col14,
        header_row=3,
        grade_col=14,
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
        grade_col=14,
        price_col_start=15,
        price_col_end=20,
        data_row_start=10,
        data_row_end=11,
        grades=_COLD_ROLL_NORMAL_GRADES,
    ),
    # 3. 高强冷轧卷宽度加减价（宽度列头为特殊格式：<900/<1000/...）
    _WidthRegion(
        title="冷轧卷板（高强）",
        category="冷轧卷板（高强）",
        grade_value_fn=_grade_from_col15,
        header_row=13,
        grade_col=14,
        price_col_start=15,
        price_col_end=19,
        data_row_start=14,
        data_row_end=14,
        grades=_COLD_ROLL_HIGH_STRENGTH_GRADES,
        is_width_special=True,
    ),
    # 4. 镀锌卷板（非高强）
    _WidthRegion(
        title="镀锌卷板（非高强）",
        category="镀锌卷板（非高强）",
        grade_value_fn=_grade_from_col15,
        header_row=22,
        grade_col=14,
        price_col_start=15,
        price_col_end=19,
        data_row_start=23,
        data_row_end=23,
        grades=_GALVANIZED_NORMAL_GRADES,
    ),
    # 5. 镀锌卷板（高强）  H300LAD及以上低合金、HC250/450DPD及以上双相钢、HC380/590TRD及以上
    _WidthRegion(
        title="镀锌卷板（高强）",
        category="镀锌卷板（高强）",
        grade_value_fn=_grade_from_col15,
        header_row=26,
        grade_col=14,
        price_col_start=15,
        price_col_end=19,
        data_row_start=27,
        data_row_end=27,
        grades=_GALVANIZED_HIGH_STRENGTH_GRADES_1,
    ),
    # 6. 镀锌卷板（高强）  CR240LA、H260YD、H260LAD、H260PD、M260LYD
    _WidthRegion(
        title="镀锌卷板（高强）",
        category="镀锌卷板（高强）",
        grade_value_fn=_grade_from_col15,
        header_row=29,
        grade_col=14,
        price_col_start=15,
        price_col_end=19,
        data_row_start=30,
        data_row_end=30,
        grades=_GALVANIZED_HIGH_STRENGTH_GRADES_2,
    ),
]


# ============================================================================
#  辅助函数
# ============================================================================

def _to_int_price(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _parse_thickness_label(label: str) -> Tuple[Optional[float], str, Optional[float], str]:
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


def _parse_width_boundary(text: str) -> Tuple[Optional[Decimal], str, Optional[Decimal], str]:
    """解析宽度边界，返回 (min_val, min_op, max_val, max_op)"""
    if not text:
        return None, ">=", None, "<"

    text = str(text).strip()

    # 复合：1000≤宽度≤1250
    m = re.match(r"^(\d+)\s*[≤<=]+\s*宽?\s*[≤<=]+\s*(\d+)$", text)
    if m:
        return Decimal(m.group(1)), ">=", Decimal(m.group(2)), "<="

    # 1250＜宽度≤1500
    m = re.match(r"^(\d+)\s*[＜<]+\s*宽?\s*[≤<=]+\s*(\d+)$", text)
    if m:
        return Decimal(m.group(1)), ">", Decimal(m.group(2)), "<="

    # 1000≤宽度＜1250
    m = re.match(r"^(\d+)\s*[≤<=]+\s*宽?\s*[＜<]+\s*(\d+)$", text)
    if m:
        return Decimal(m.group(1)), ">=", Decimal(m.group(2)), "<"

    # 纯下界：≥1000
    m = re.match(r"^[≥>=]+\s*(\d+)$", text)
    if m:
        return Decimal(m.group(1)), ">=", None, "<"

    # 纯上界：<1000
    m = re.match(r"^[＜<=]+\s*(\d+)$", text)
    if m:
        return None, ">=", Decimal(m.group(1)), "<"

    return None, ">=", None, "<"


def _infer_width_boundaries(
    raw: Dict[int, Tuple[Optional[Decimal], str, Optional[Decimal], str]],
    price_cols: List[int],
) -> Dict[int, Tuple[Optional[Decimal], str, Optional[Decimal], str]]:
    """推断完整边界：补全 min/max 为 None 的列"""
    result: Dict[int, Tuple[Optional[Decimal], str, Optional[Decimal], str]] = {}
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
                next_min, _, _, _ = raw[next_c]
                if next_min is not None:
                    max_val = next_min
                    max_op = "<"

        result[c] = (min_val, min_op, max_val, max_op)

    return result


def _parse_width_boundary_cold_high_strength(
    price_cols: List[int],
) -> Dict[int, Tuple[Optional[Decimal], str, Optional[Decimal], str]]:
    """冷轧卷板（高强）特殊宽度边界：列头文本 <900 <1000 ... 与实际含义不符。

    实际映射（固定写死）：
        col15 <900        → w < 900
        col16 <1000       → 900 <= w < 1000   （<1000 实际是第二段）
        col17 1000≤w<1400 → 1000 <= w < 1400
        col18 1400≤w<1500 → 1400 <= w < 1500
        col19 ≥1500       → w >= 1500
    """
    result: Dict[int, Tuple[Optional[Decimal], str, Optional[Decimal], str]] = {}

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


# ============================================================================
#  Handler
# ============================================================================

class MagangSheetHandler(BaseSheetHandler):
    """马钢 Sheet 处理器（旧版格式）。使用固定区域逐行读取 N2:T33 六类宽度加减价。"""

    def parse(
        self,
        sheet: Worksheet,
        steel_mill: str,
        warnings: List[str],
    ) -> List:
        policies: List = []
        policies.extend(self._parse_thickness_fixed(sheet, steel_mill))
        policies.extend(self._parse_width_fixed(sheet, steel_mill, warnings))
        policies.extend(self.parse_zinc_coating_blocks(sheet, steel_mill))
        return policies

    # ------------------------------------------------------------------ #
    #  固定区域宽度解析
    # ------------------------------------------------------------------ #

    def _parse_width_fixed(
        self, sheet: Worksheet, steel_mill: str, warnings: List[str]
    ) -> List:
        policies: List = []
        for region in _WIDTH_REGIONS:
            policies.extend(self._parse_one_region(sheet, steel_mill, region, warnings))
        return policies

    def _parse_one_region(
        self,
        sheet: Worksheet,
        steel_mill: str,
        region: _WidthRegion,
        warnings: List[str],
    ) -> List:
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
        raw_boundaries: Dict[int, Tuple[Optional[Decimal], str, Optional[Decimal], str]] = {}
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

        # Step 3: 确定钢种列表
        # grades 不为空 -> 使用 region.grades 中的钢种列表（板类）
        # grades 为空 -> 使用行数据中的 grade_value（冷轧卷类）
        if region.grades:
            steel_grades = region.grades
            use_row_grade = False
        else:
            steel_grades = None
            use_row_grade = True

        # Step 4: 对每个钢种构建 policy
        policies: List = []
        if use_row_grade:
            # 冷轧卷类：使用行数据中的 grade_value
            for r, grade_value in grade_rows_with_value:
                items = self._build_width_items(sheet, r, price_cols, boundaries)
                if not items:
                    continue

                policies.append(ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=region.category,
                    grade_type=GRADE_TYPE_THICKNESS_RANGE,
                    grade_value=grade_value,
                    policy_type=POLICY_TYPE_WIDTH,
                    base_thickness=None,
                    items=items,
                ))
        else:
            # 板类：每行代表一个厚度范围，每个钢种共用该行的价格数据
            for row_idx, (data_row, _) in enumerate(grade_rows_with_value):
                items = self._build_width_items(sheet, data_row, price_cols, boundaries)
                if not items:
                    continue

                for grade_value in steel_grades:
                    policies.append(ParsedPolicy(
                        steel_mill=steel_mill,
                        category_name=region.category,
                        grade_type=GRADE_TYPE_THICKNESS_RANGE,
                        grade_value=grade_value,
                        policy_type=POLICY_TYPE_WIDTH,
                        base_thickness=None,
                        items=items,
                    ))

        return policies
    def _build_width_items(
        self,
        sheet: Worksheet,
        row: int,
        price_cols: List[int],
        boundaries: Dict[int, Tuple[Optional[Decimal], str, Optional[Decimal], str]],
    ) -> List[ParsedLadderItem]:
        """构建某行的宽度阶梯 items（同时解析厚度范围标签）"""
        # 厚度标签：先查 col14，再查 col15
        thick_label = ""
        for c in [14, 15]:
            v = sheet.cell(row=row, column=c).value
            if v is not None:
                thick_label = str(v).strip()
                break
        thick_min, thick_min_op, thick_max, thick_max_op = _parse_thickness_label(thick_label)

        items: List[ParsedLadderItem] = []
        sorted_cols = sorted(price_cols)

        for i, c in enumerate(sorted_cols):
            if c not in boundaries:
                continue

            min_val, min_op, max_val, max_op = boundaries[c]
            price = _to_int_price(sheet.cell(row=row, column=c).value)

            if price == 0 and min_val is None and max_val is None:
                continue

            items.append(ParsedLadderItem(
                target_sub_group=None,
                thick_min=Decimal(str(thick_min)) if thick_min is not None else None,
                thick_min_operator=thick_min_op,
                thick_max=Decimal(str(thick_max)) if thick_max is not None else None,
                thick_max_operator=thick_max_op,
                width_min=min_val,
                width_min_operator=min_op,
                width_max=max_val,
                width_max_operator=max_op,
                price_adjustment=price,
                is_base=False,
                sort_order=row * 100 + i,
            ))

        return items

    # ------------------------------------------------------------------ #
    #  厚度解析（复用默认逻辑）
    # ------------------------------------------------------------------ #

    def _parse_thickness_fixed(
        self, sheet: Worksheet, steel_mill: str
    ) -> List:
        blocks = self.find_default_thickness_blocks(sheet, steel_mill, max_col=13)
        policies: List = []
        for block in blocks:
            policies.extend(
                self.assembler.build_policies_from_block(sheet, steel_mill, block)
            )
        return policies