"""Sheet 处理器基类。

职责：承载所有公共逻辑，子类只实现：
1. `find_thickness_blocks(sheet, steel_mill)` — 找到本 Sheet 所有厚度块描述
2. `find_width_blocks(sheet, steel_mill)` — 找到本 Sheet 所有宽度块描述

块描述 = {
    "category_name": str,
    "policy_type": str,          # "THICKNESS" 或 "WIDTH"
    "grade_col": int,            # 钢种列
    "header_row": int,           # 列头行（含 boundary）
    "price_cols": List[int],     # 价格列
    "data_row_start": int,
    "data_row_end": int,
    "base_thickness": Decimal | None,
}

厚度块描述（policy_type="THICKNESS"）：
- 列头格式：如 "＜0.5" → 上限不含, "0.5-0.8" → 区间, "≥2.0" → 下限
- 数据列：每列对应一个厚度区间，值为加减价（元/吨）
- 边界推断：最后一列无上界时按 base_thickness 推断；中间列根据下一列下界推断上界

宽度块描述（policy_type="WIDTH"）：
- 列头格式：如 "＜900" → 上限不含, "900≤W＜1600" → 区间, "≥1600" → 下限
- 数据列：每列对应一个宽度区间，值为加减价（元/吨）
- 边界推断：最后一列无上界时为 +∞；中间列根据下一列下界推断上界

基类负责：给定块描述 → List[ParsedPolicy] 的通用解析。
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from openpyxl.worksheet.worksheet import Worksheet

from ..boundary_parser import _Boundary, _parse_boundary
from ..models import ParsedLadderItem, ParsedPolicy
from ..models.policy import GRADE_TYPE_CATEGORY, GRADE_TYPE_GRADE, GRADE_TYPE_THICKNESS_RANGE, GRADE_TYPE_WIDTH_RANGE
from ..value_parser import _to_int_price, _to_str, _to_str_or_none
from .constants import BENCH_PATTERN, BLANK_LIMIT, CATEGORY_HINTS, GRADE_LABELS, THICKNESS_HEADER_KEYWORDS

# 宽度范围关键字（用于推断 grade_type = WIDTH_RANGE）
_WIDTH_RANGE_KEYWORDS = ("≤", "≥", "＜", "＞", "W", "宽")

# 已知钢材类别（用于推断 grade_type = CATEGORY）
_CATEGORY_NAMES: frozenset[str] = frozenset({"冷轧钢", "镀锌钢", "酸洗钢", "热轧钢"})

# 厚度范围关键字（用于推断 grade_type = THICKNESS_RANGE）
_THICKNESS_RANGE_KEYWORDS: tuple[str, ...] = ("厚度",)


class BaseSheetHandler:
    """Sheet 处理器基类。"""

    def parse(
        self,
        sheet: Worksheet,
        steel_mill: str,
        warnings: List[str],
    ) -> List[ParsedPolicy]:
        """解析入口：子类通过 find_thickness_blocks / find_width_blocks 描述块，交基类执行。"""
        policies: List[ParsedPolicy] = []
        policies.extend(self._parse_blocks(sheet, steel_mill, "THICKNESS"))
        policies.extend(self._parse_blocks(sheet, steel_mill, "WIDTH"))
        return policies

    # ------------------------------------------------------------------ #
    # 子类需要实现的方法（返回块描述列表）
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """返回本 Sheet 所有厚度块的描述。默认返回空，子类覆写。"""
        return []

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """返回本 Sheet 所有宽度块的描述。默认返回空，子类覆写。"""
        return []

    # ------------------------------------------------------------------ #
    # 子类复用的默认厚度块查找（默认 max_col = sheet 全列）
    # ------------------------------------------------------------------ #

    def find_default_thickness_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        max_col: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """默认厚度块扫描: 多个厚度块在左侧垂直堆叠.

        关键点:
        1. label_row 集合用 find_grade_label_rows 找出
        2. 每个块的边界 = next_label_row - 1, 强制截断
           (避免 find_block_end_row 因下个 label_row 非空而跨块合并)
        3. 块的 category 由本块 grade 后缀或 label_row 上方关键字推断
        """
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = max_col if max_col is not None else self.col_max(sheet)
        last_end = 0

        # 一次性找全所有 label_rows (天然块边界)
        all_label_rows = self.find_grade_label_rows(sheet, 1, max_row)

        while True:
            label_rows = [lr for lr in all_label_rows if lr > last_end]
            if not label_rows:
                break
            label_row = label_rows[0]
            # 块下界 = min( next_label_row - 1, 其它边界信号 )
            next_label = label_rows[1] if len(label_rows) > 1 else None
            if next_label is not None:
                block_end = next_label - 1
            else:
                # 最后一块: 用 find_block_end_row, 但允许 "宽度加减价" / "宽度加价"
                # 作为"块结束信号"避免吸入后面的宽度块
                block_end = self._find_thickness_block_end_with_width_hint(
                    sheet, label_row + 1, max_row, max_col
                )

            if block_end <= label_row + 1:
                last_end = label_row + 1
                continue

            block = self.locate_thickness_block(sheet, label_row, block_end, max_col)
            if block:
                # 若字面没命中 category, 用 grade 后缀再推断一次
                block["category_name"] = self.infer_block_category(
                    sheet, block, max_col=max_col
                )
                blocks.append(block)
                last_end = block["data_row_end"]
            else:
                last_end = label_row + 1

        return blocks

    def _find_thickness_block_end_with_width_hint(
        self,
        sheet: Worksheet,
        start_row: int,
        max_row: int,
        max_col: int,
        *,
        blank_limit: int = BLANK_LIMIT,
    ) -> int:
        """向下扫描块末尾, 但提前停在出现宽度标题的行.

        触发条件: col 1 含 "宽度加减价" 或 "宽度加价" 字面.
        这让最末尾的厚度块不会跨过宽度标题.
        """
        blank_streak = 0
        for r in range(start_row, max_row + 1):
            text = self.text(sheet, r, 1)
            if text and ("宽度加减价" in text or "宽度加价" in text):
                # 块到此为止; trim_block_end 会再回退去末尾空行
                return max(start_row, r - 1)
            has_value = any(
                _to_str(sheet.cell(row=r, column=c).value)
                for c in range(1, max_col + 1)
            )
            blank_streak = 0 if has_value else blank_streak + 1
            if blank_streak >= blank_limit:
                return r - blank_limit
        return max_row

    # ------------------------------------------------------------------ #
    # 块解析（通用）
    # ------------------------------------------------------------------ #

    def _parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List[ParsedPolicy]:
        """给定块描述列表，执行通用解析。"""
        blocks = (
            self.find_thickness_blocks(sheet, steel_mill)
            if policy_type == "THICKNESS"
            else
            self.find_width_blocks(sheet, steel_mill)
        )
        policies: List[ParsedPolicy] = []
        for block in blocks:
            policies.extend(
                self._parse_one_block(sheet, steel_mill, policy_type, block)
            )
        return policies

    def _parse_one_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
        block: Dict[str, Any],
    ) -> List[ParsedPolicy]:
        """给定单个块描述，解析出 ParsedPolicy 列表。"""
        grade_col = block.get("grade_col")
        header_row = block["header_row"]
        price_cols = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")
        base_thickness = block.get("base_thickness")
        grade_blacklist = block.get("grade_blacklist", GRADE_LABELS)

        boundaries = self._collect_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        # 排序列号，便于推断上界
        sorted_price_cols = sorted(price_cols)

        policies: List[ParsedPolicy] = []
        last_grade: Optional[str] = None  # 用于合并单元格的钢种继承
        for r in range(data_start, data_end + 1):
            # grade_col 为 None 时（如首钢宽度块），直接跳到下一行
            if grade_col is None:
                continue
            grade = self.text_or_none(sheet, r, grade_col)
            # 合并单元格处理：钢种列为空时继承上一行的值
            if not grade:
                grade = last_grade
            else:
                last_grade = grade  # 更新继承值
            if not grade:
                continue
            if grade in grade_blacklist:
                continue
            # 推断 grade_type
            grade_type = self._infer_grade_type(grade, policy_type)
            items = self._build_items_for_row(sheet, r, sorted_price_cols, boundaries, policy_type, sort_order=r)
            if not items:
                continue
            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=category_name,
                    grade_type=grade_type,
                    grade_value=grade,
                    policy_type=policy_type,
                    base_thickness=base_thickness,
                    items=items,
                )
            )
        return policies

    def _infer_grade_type(self, grade: str, policy_type: str) -> str:
        """推断 grade 的语义类型。

        规则:
        - THICKNESS 政策：grade 必定是钢种牌号
        - WIDTH 政策：grade 可能是钢种牌号、宽度范围、厚度范围或类别名
          * 含宽度关键字（≤/≥/W/宽）→ WIDTH_RANGE
          * 含"厚度"关键字 → THICKNESS_RANGE
          * 是已知类别名（冷轧钢/镀锌钢/酸洗钢）→ CATEGORY
          * 否则 → GRADE（钢种牌号）
        """
        if policy_type == "THICKNESS":
            return GRADE_TYPE_GRADE
        # WIDTH 政策：需要区分类型
        grade_stripped = grade.strip()
        if any(kw in grade_stripped for kw in _WIDTH_RANGE_KEYWORDS):
            return GRADE_TYPE_WIDTH_RANGE
        if any(kw in grade_stripped for kw in _THICKNESS_RANGE_KEYWORDS):
            return GRADE_TYPE_THICKNESS_RANGE
        if grade_stripped in _CATEGORY_NAMES:
            return GRADE_TYPE_CATEGORY
        return GRADE_TYPE_GRADE

    def _collect_boundaries(
        self, sheet: Worksheet, header_row: int, price_cols: List[int]
    ) -> Dict[int, _Boundary]:
        result = {}
        for c in price_cols:
            v = sheet.cell(row=header_row, column=c).value
            b = _parse_boundary(v)
            if b is not None:
                result[c] = b
        return result

    def find_start_row(
        self,
        sheet: Worksheet,
        row: int,
        col: int,
    ) -> Optional[int]:
        """检查单元格是否在合并区域内，如果是，返回合并区域的起始行号。

        在 openpyxl 中，合并单元格的起始单元格（top-left cell）存储值，
        其他合并单元格（被合并的）的值为 None。
        此方法通过检查合并单元格范围来确定当前单元格是否属于某个合并区域。

        Args:
            sheet: Excel 工作表
            row: 当前行号（1-indexed）
            col: 当前列号（1-indexed）

        Returns:
            如果单元格属于合并区域，返回合并区域的起始行号；否则返回 None
        """

        for merged_range in sheet.merged_cells:
            if merged_range.min_row <= row <= merged_range.max_row and merged_range.min_col <= col <= merged_range.max_col:
                # 当前单元格在合并区域内，返回合并区域的起始行
                return merged_range.min_row

        return None

    def _find_value_above(
        self,
        sheet: Worksheet,
        start_row: int,
        col: int,
        min_row: int = 1,
    ) -> int:
        """
        向上查找非 None 值。

        当合并区域的起始单元格也被 openpyxl 返回为 None 时，
        向上查找最近的非 None 值。

        Args:
            sheet: Excel 工作表
            start_row: 起始行号（包含）
            col: 列号
            min_row: 最小行号（不查询此行以上）

        Returns:
            找到的非 None 值的整数形式，未找到返回 0
        """
        for r in range(start_row - 1, min_row - 1, -1):
            val = sheet.cell(row=r, column=col).value
            if val is not None:
                return _to_int_price(val)
        return 0

    def _build_items_for_row(
        self,
        sheet: Worksheet,
        r: int,
        price_cols: List[int],
        boundaries: Dict[int, _Boundary],
        policy_type: str = "THICKNESS",
        sort_order: int = 0,
    ) -> List[ParsedLadderItem]:
        items: List[ParsedLadderItem] = []
        sorted_cols = sorted(price_cols)
        for i, c in enumerate(sorted_cols):
            if c not in boundaries:
                continue
            # 获取加减价金额。如果当前行的值为空，检查开始行是否合并到此处。
            # 如果是合并到此处，则使用开始行的值。
            # 注意：合并区域的起始单元格也可能被 openpyxl 返回为 None，
            # 此时需要继续向上查找非 None 值。
            price_cell = sheet.cell(row=r, column=c)
            if price_cell.value is None:
                start_row = self.find_start_row(sheet, r, c)
                if start_row is not None:
                    # 尝试获取起始单元格的值
                    start_val = sheet.cell(row=start_row, column=c).value
                    if start_val is not None:
                        price = _to_int_price(start_val)
                    else:
                        # 起始单元格的值也为 None，继续向上查找非 None 值
                        price = self._find_value_above(sheet, start_row, c)
                else:
                    price = 0
            else:
                price = _to_int_price(price_cell.value)

            boundary = boundaries[c]

            # 推断上界：仅当当前列已有 max_val 时跳过
            if boundary.max_val is None and i < len(sorted_cols) - 1:
                next_c = sorted_cols[i + 1]
                if next_c in boundaries:
                    next_boundary = boundaries[next_c]
                    if next_boundary.min_val is not None:
                        boundary.max_val = next_boundary.min_val
                        boundary.max_operator = "<"

            if policy_type == "THICKNESS":
                # 厚度政策：只设置厚度维度
                items.append(
                    ParsedLadderItem(
                        target_sub_group=None,
                        thick_min=boundary.min_val,
                        thick_min_operator=boundary.min_operator,
                        thick_max=boundary.max_val,
                        thick_max_operator=boundary.max_operator,
                        width_min=None,
                        width_min_operator=">=",
                        width_max=None,
                        width_max_operator="<",
                        price_adjustment=price,
                        is_base=False,
                        sort_order=sort_order,
                    )
                )
            else:
                # 宽度政策：只设置宽度维度
                items.append(
                    ParsedLadderItem(
                        target_sub_group=None,
                        thick_min=None,
                        thick_min_operator=">=",
                        thick_max=None,
                        thick_max_operator="<",
                        width_min=boundary.min_val,
                        width_min_operator=boundary.min_operator,
                        width_max=boundary.max_val,
                        width_max_operator=boundary.max_operator,
                        price_adjustment=price,
                        is_base=False,
                        sort_order=sort_order,
                    )
                )
        return items

    def build_item(
        self, boundary: _Boundary, price: int, width_boundary: Optional[_Boundary] = None
    ) -> ParsedLadderItem:
        """构建阶梯明细项。

        Args:
            boundary: 厚度边界（或单一维度边界）
            price: 加减价金额
            width_boundary: 可选的宽度边界（用于 WIDTH 类型政策）
        """
        if width_boundary is not None:
            # 双维度：同时有厚度和宽度
            return ParsedLadderItem(
                target_sub_group=None,
                thick_min=boundary.min_val,
                thick_min_operator=boundary.min_operator,
                thick_max=boundary.max_val,
                thick_max_operator=boundary.max_operator,
                width_min=width_boundary.min_val,
                width_min_operator=width_boundary.min_operator,
                width_max=width_boundary.max_val,
                width_max_operator=width_boundary.max_operator,
                price_adjustment=price,
                is_base=False,
                sort_order=0,
            )
        else:
            # 单维度：只有厚度
            return ParsedLadderItem(
                target_sub_group=None,
                thick_min=boundary.min_val,
                thick_min_operator=boundary.min_operator,
                thick_max=boundary.max_val,
                thick_max_operator=boundary.max_operator,
                width_min=None,
                width_min_operator=">=",
                width_max=None,
                width_max_operator="<",
                price_adjustment=price,
                is_base=False,
                sort_order=0,
            )

    # ------------------------------------------------------------------ #
    # 公共读取工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def cell(sheet: Worksheet, r: int, c: int) -> Any:
        return sheet.cell(row=r, column=c).value

    @staticmethod
    def text(sheet: Worksheet, r: int, c: int) -> str:
        return _to_str(sheet.cell(row=r, column=c).value)

    @staticmethod
    def text_or_none(sheet: Worksheet, r: int, c: int) -> Optional[str]:
        return _to_str_or_none(sheet.cell(row=r, column=c).value)

    @staticmethod
    def row_max(sheet: Worksheet) -> int:
        return sheet.max_row or 0

    @staticmethod
    def col_max(sheet: Worksheet) -> int:
        return sheet.max_column or 0

    # ------------------------------------------------------------------ #
    # 扫描工具
    # ------------------------------------------------------------------ #

    def find_row_with_keywords(
        self,
        sheet: Worksheet,
        keywords: tuple[str, ...],
        *,
        start_row: int = 1,
        end_row: Optional[int] = None,
        scan_col: Optional[int] = None,
    ) -> Optional[int]:
        end_row = end_row or self.row_max(sheet)
        for r in range(start_row, end_row + 1):
            cols = [scan_col] if scan_col is not None else range(1, self.col_max(sheet) + 1)
            for c in cols:
                text = _to_str(sheet.cell(row=r, column=c).value)
                if text and any(kw in text for kw in keywords):
                    return r
        return None

    def find_grade_label_rows(
        self,
        sheet: Worksheet,
        start_row: int = 1,
        end_row: Optional[int] = None,
    ) -> List[int]:
        """返回所有钢种标签行（col 1）行号。"""
        end_row = end_row or self.row_max(sheet)
        rows = []
        for r in range(start_row, end_row + 1):
            if self.text(sheet, r, 1) in GRADE_LABELS:
                rows.append(r)
        return rows

    def find_thickness_title_row(
        self,
        sheet: Worksheet,
        start_row: int,
        end_row: int,
        *,
        scan_cols: Optional[List[int]] = None,
    ) -> Optional[int]:
        """在 start_row ~ end_row 内找首个含厚度关键字的行。"""
        max_col = scan_cols[-1] if scan_cols else self.col_max(sheet)
        for r in range(start_row, min(start_row + 5, end_row + 1)):
            for c in (scan_cols or range(1, max_col + 1)):
                text = _to_str(sheet.cell(row=r, column=c).value)
                if text and any(kw in text for kw in THICKNESS_HEADER_KEYWORDS):
                    return r
        return None

    def find_header_row(
        self,
        sheet: Worksheet,
        start_row: int,
        end_row: int,
        *,
        scan_cols: Optional[List[int]] = None,
    ) -> Optional[int]:
        """在 start_row ~ end_row 内找首个含 boundary 的行（列头行）。"""
        max_col = scan_cols[-1] if scan_cols else self.col_max(sheet)
        for r in range(start_row, min(start_row + 5, end_row + 1)):
            for c in (scan_cols or range(1, max_col + 1)):
                if _parse_boundary(sheet.cell(row=r, column=c).value) is not None:
                    return r
        return None

    def collect_price_cols(
        self,
        sheet: Worksheet,
        header_row: int,
        start_col: int = 2,
        end_col: Optional[int] = None,
    ) -> List[int]:
        """在 header_row 上收集所有含 boundary 的列。"""
        end_col = end_col or self.col_max(sheet)
        cols = []
        for c in range(start_col, end_col + 1):
            if _parse_boundary(sheet.cell(row=header_row, column=c).value) is not None:
                cols.append(c)
        return cols

    def find_block_end_row(
        self,
        sheet: Worksheet,
        start_row: int,
        max_row: int,
        max_col: int,
        *,
        blank_limit: int = BLANK_LIMIT,
        scan_cols: Optional[List[int]] = None,
    ) -> int:
        """向下扫描，遇连续 blank_limit 个空行则停。

        Args:
            scan_cols: 若指定，只扫描这些列；否则扫描 1..max_col。
        """
        blank_streak = 0
        cols = scan_cols if scan_cols is not None else list(range(1, max_col + 1))
        for r in range(start_row, max_row + 1):
            has_value = any(
                _to_str(sheet.cell(row=r, column=c).value)
                for c in cols
            )
            blank_streak = 0 if has_value else blank_streak + 1
            if blank_streak >= blank_limit:
                return r - blank_limit
        return max_row

    def trim_block_end(
        self,
        sheet: Worksheet,
        header_row: int,
        block_end_row: int,
        max_col: int,
        *,
        scan_cols: Optional[List[int]] = None,
        skip_grade_keywords: bool = False,
        grade_col: int = 1,
    ) -> int:
        """从 block_end_row 向上回退，去掉末尾空行。

        Args:
            scan_cols: 若指定，只扫描这些列；否则扫描 1..max_col。
            skip_grade_keywords: 若为 True，跳过 grade 列含 GRADE_LABELS 关键字的行
                                 （如"钢种"行），用于马钢这种左侧厚度块 grade 列
                                 仍可能渗入右侧宽度块区域的场景。
            grade_col: grade 所在列号，skip_grade_keywords 为 True 时使用。
        """
        cols = scan_cols if scan_cols is not None else list(range(1, max_col + 1))
        for r in range(block_end_row, header_row, -1):
            if skip_grade_keywords and grade_col in cols:
                v = sheet.cell(row=r, column=grade_col).value
                if v is not None and str(v).strip() in GRADE_LABELS:
                    continue  # 跳过 grade 标题行
            # 检查该行是否有数据（直接值或合并单元格区域内）
            has_data = False
            for c in cols:
                cell_val = sheet.cell(row=r, column=c).value
                if cell_val is not None:
                    has_data = True
                    break
                # 值为 None → 可能在合并单元格区域内，检查合并范围
                if self.find_start_row(sheet, r, c) is not None:
                    # 合并区域的起始单元格应有值（openpyxl 会读到）
                    start_r = self.find_start_row(sheet, r, c)
                    merged_val = sheet.cell(row=start_r, column=c).value
                    if merged_val is not None:
                        has_data = True
                        break
            if has_data:
                return r
        return header_row

    # ------------------------------------------------------------------ #
    # 扫描工具 - 边界信号
    # ------------------------------------------------------------------ #

    _SECTION_BREAK_KEYWORDS: tuple[str, ...] = (
        # 类目标题行 (新块开始)
        "厚度加减价", "厚度(mm)", "厚度（mm）",
        "宽度加减价", "宽度加价", "宽度(mm)", "宽度（mm）",
    )

    def find_section_break_row(
        self,
        sheet: Worksheet,
        start_row: int,
        max_row: int,
        scan_col: int = 1,
    ) -> Optional[int]:
        """从 start_row 起向下扫描, 找到第一个"段标题"行 (新块开始).

        段标题关键字: 厚度加减价/厚度(mm)/宽度加减价/宽度加价
        命中即返回行号.
        """
        for r in range(start_row, max_row + 1):
            text = self.text(sheet, r, scan_col)
            if not text:
                continue
            for kw in self._SECTION_BREAK_KEYWORDS:
                if kw in text:
                    return r
        return None

    # ------------------------------------------------------------------ #
    # 推断工具
    # ------------------------------------------------------------------ #

    def infer_base_thickness(
        self,
        sheet: Worksheet,
        header_row: int,
        label_row: int,
        max_col: int,
    ) -> Optional[Decimal]:
        """在 header_row 附近（向上 3 行）查找 `基准厚度 X.X`。"""
        for r in range(max(1, label_row - 3), header_row + 1):
            for c in range(1, max_col + 1):
                text = _to_str(sheet.cell(row=r, column=c).value)
                if not text:
                    continue
                m = BENCH_PATTERN.search(text)
                if m:
                    return Decimal(m.group(1))
        return None

    def infer_category(
        self,
        sheet: Worksheet,
        label_row: int,
        max_col: int,
    ) -> str:
        """在 label_row 上方 6 行内查找分类关键字。"""
        for r in range(max(1, label_row - 6), label_row):
            for c in range(1, max_col + 1):
                text = _to_str(sheet.cell(row=r, column=c).value)
                if not text:
                    continue
                for hint in CATEGORY_HINTS:
                    if hint in text:
                        return hint
        return "冷轧钢"

    # ------------------------------------------------------------------ #
    # 按钢种名后缀推断 category (兜底逻辑)
    # ------------------------------------------------------------------ #

    _GALVANIZED_SUFFIXES: tuple[str, ...] = ("+Z", "+ZF", "+ZM", "+ZA", "+AZ")
    _PICKLED_SUFFIXES: tuple[str, ...] = ("+A",)

    # 已知酸洗钢种名（行业通用，无固定后缀）
    _PICKLED_GRADES: frozenset[str] = frozenset({
        "SPHC", "SPHD", "SPHE", "SPHF",
        "SAPH370", "SAPH400", "SAPH440",
        "QStE340TM", "QStE380TM", "QStE420TM", "QStE460TM", "QStE500TM",
        "QSTE420TM", "QSTE460TM", "QSTE500TM",
        "B510L", "B590L",
    })

    def category_from_grade_name(self, grade: str) -> str:
        """按钢种名后缀/名称推断 category, 用于 sheet 标题里无字面分类关键字时.

        业务约束: 同一厚度块内钢种都是同一类 (冷轧/镀锌/酸洗).
        镀锌以 +Z 后缀识别; 酸洗按已知名单 (SPHC/SAPH/QStE 等).
        """
        if not grade:
            return "冷轧钢"
        for suf in self._GALVANIZED_SUFFIXES:
            if grade.endswith(suf):
                return "镀锌钢"
        # 优先按已知名单判断酸洗 (覆盖 SPHC/SAPH/QStE 等)
        if grade in self._PICKLED_GRADES:
            return "酸洗钢"
        for suf in self._PICKLED_SUFFIXES:
            if grade.endswith(suf):
                return "酸洗钢"
        return "冷轧钢"

    def infer_block_category(
        self,
        sheet: Worksheet,
        block: Dict[str, Any],
        *,
        max_col: int = 14,
    ) -> str:
        """综合 '字面 hint' 与 'grade 后缀' 推断块的 category.

        优先级:
        1. 若块标题行上方 6 行内出现 CATEGORY_HINTS, 用该字面
           (这是旧 infer_category 的逻辑, 保留以防漏判)
        2. 否则按块内 grade 后缀推断
        """
        label_row = block.get("header_row", 0) - 1  # header_row - 1 才是 label_row 附近
        # 用 locate_thickness_block 已经写过 category_name, 先取
        literal_cat = block.get("category_name") or "冷轧钢"
        # 若 locate_thickness_block 已经从字面拿到了非默认 ("冷轧钢") 值, 直接信任
        if literal_cat != "冷轧钢":
            return literal_cat

        # 否则扫块内 grade 按后缀推断
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        grade_col = block.get("grade_col", 1)
        galvanized = pickled = cold = 0
        for r in range(data_start, data_end + 1):
            v = sheet.cell(row=r, column=grade_col).value
            if v is None:
                continue
            t = str(v).strip()
            if not t:
                continue
            if t in GRADE_LABELS:
                continue
            cat = self.category_from_grade_name(t)
            if cat == "镀锌钢":
                galvanized += 1
            elif cat == "酸洗钢":
                pickled += 1
            else:
                cold += 1

        if galvanized and not cold:
            return "镀锌钢"
        if pickled and not cold:
            return "酸洗钢"
        if galvanized and cold:
            # 跨度过大误判 → 取多者
            if galvanized > cold:
                return "镀锌钢"
            if pickled > cold:
                return "酸洗钢"
            return "冷轧钢"
        if pickled and cold:
            return "酸洗钢" if pickled > cold else "冷轧钢"
        return "冷轧钢"

    # ------------------------------------------------------------------ #
    # 组合工具：厚度块 5 步定位
    # ------------------------------------------------------------------ #

    def locate_thickness_block(
        self,
        sheet: Worksheet,
        label_row: int,
        block_end: int,
        max_col: int,
    ) -> Optional[Dict[str, Any]]:
        """执行厚度块的 5 步定位，返回块描述或 None。"""
        title_row = self.find_thickness_title_row(
            sheet, label_row, block_end, scan_cols=list(range(2, max_col + 1))
        )
        if title_row is None:
            return None

        header_row = self.find_header_row(
            sheet, title_row + 1, block_end, scan_cols=list(range(2, max_col + 1))
        )
        if header_row is None:
            return None

        price_cols = self.collect_price_cols(sheet, header_row, start_col=2, end_col=max_col)
        if not price_cols:
            return None

        data_end = self.trim_block_end(sheet, header_row, block_end, max_col)
        base_thickness = self.infer_base_thickness(sheet, header_row, label_row, max_col)
        category = self.infer_category(sheet, label_row, max_col)

        return {
            "category_name": category,
            "policy_type": "THICKNESS",
            "grade_col": 1,
            "header_row": header_row,
            "price_cols": price_cols,
            "data_row_start": header_row + 1,
            "data_row_end": data_end,
            "base_thickness": base_thickness,
            "grade_blacklist": GRADE_LABELS,
        }

    # ------------------------------------------------------------------ #
    # 组合工具：宽度块定位（子类 find_width_blocks 通用复用）
    # ------------------------------------------------------------------ #

    def locate_width_block(
        self,
        sheet: Worksheet,
        title_row: int,
        block_end: int,
        grade_col: int,
        data_col_start: int,
        max_col: int,
        *,
        category: str = "冷轧钢",
        header_row_offset: int = 1,
        title_col: int = 1,
        scan_cols: Optional[List[int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """执行宽度块的 3 步定位（列头行 → 收集价格列 → 末尾回退），返回块描述。

        Args:
            title_row: 宽度块标题行（含关键字，如"宽度加价"）
            block_end: 该块数据行下界
            grade_col: 钢种列号
            data_col_start: 价格列起始列号（边界列）
            max_col: Sheet 最大列
            category: 类目名称
            header_row_offset: 列头行相对标题行的偏移（默认 +1）
            title_col: 标题所在列（用于读取 category 推断）
            scan_cols: 扫描数据存在性时限定列范围；若 None 则扫描 1..max_col。
        """
        header_row = title_row + header_row_offset
        if header_row > block_end:
            return None

        price_cols = self.collect_price_cols(
            sheet, header_row, start_col=data_col_start, end_col=max_col
        )
        if not price_cols:
            return None

        data_start = header_row + 1
        # trim_block_end 扫描宽度列（+grade_col）判断真实数据末行
        # scan_cols 必须包含 grade 列，否则只有价格列为空但 grade 列有值的行被误判
        effective_scan_cols = list(scan_cols or range(1, max_col + 1))
        if grade_col not in effective_scan_cols:
            effective_scan_cols.append(grade_col)
        # skip_grade_keywords: 左侧厚度块的 grade 列可能渗入右侧宽度区域（如"钢种"行），
        # 需要跳过这些关键字行，否则 trim_block_end 误以为仍有数据
        data_end = self.trim_block_end(
            sheet, header_row, block_end, max_col,
            scan_cols=effective_scan_cols,
            skip_grade_keywords=True,
            grade_col=grade_col,
        )

        return {
            "category_name": category,
            "policy_type": "WIDTH",
            "grade_col": grade_col,
            "header_row": header_row,
            "price_cols": price_cols,
            "data_row_start": data_start,
            "data_row_end": data_end,
            "base_thickness": None,
            "grade_blacklist": GRADE_LABELS,
        }
