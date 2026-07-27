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

基类负责：给定块描述 → List[ParsedPolicy] 的通用解析。
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from openpyxl.worksheet.worksheet import Worksheet

from ..boundary_parser import _Boundary, _parse_boundary
from ..models import ParsedLadderItem, ParsedPolicy
from ..value_parser import _to_int_price, _to_str, _to_str_or_none
from .constants import BENCH_PATTERN, BLANK_LIMIT, CATEGORY_HINTS, GRADE_LABELS, THICKNESS_HEADER_KEYWORDS


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
            else self.find_width_blocks(sheet, steel_mill)
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
        grade_col = block["grade_col"]
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
        for r in range(data_start, data_end + 1):
            grade = self.text_or_none(sheet, r, grade_col)
            if not grade:
                continue
            if grade in grade_blacklist:
                continue
            items = self._build_items_for_row(sheet, r, sorted_price_cols, boundaries)
            if not items:
                continue
            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=category_name,
                    grade_name=grade,
                    policy_type=policy_type,
                    base_thickness=base_thickness,
                    items=items,
                )
            )
        return policies

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

    def _build_items_for_row(
        self,
        sheet: Worksheet,
        r: int,
        price_cols: List[int],
        boundaries: Dict[int, _Boundary],
    ) -> List[ParsedLadderItem]:
        items: List[ParsedLadderItem] = []
        # 排过序的列号列表，用于推断每个区间段的上界
        sorted_cols = sorted(price_cols)
        for i, c in enumerate(sorted_cols):
            if c not in boundaries:
                continue
            price = _to_int_price(sheet.cell(row=r, column=c).value)
            items.append(self.build_item(boundaries[c], price))
            # 推断上界：仅当当前列已有 max_val（即已限定上限，如纯数字 ≤X）时跳过，
            # 其他情况取下一列的下界作为本列的上界（左闭右开）。
            cur_has_max = boundaries[c].max_val is not None
            if cur_has_max:
                continue
            if i < len(sorted_cols) - 1:
                next_c = sorted_cols[i + 1]
                if next_c in boundaries:
                    next_boundary = boundaries[next_c]
                    if next_boundary.min_val is not None:
                        items[-1].max_val = next_boundary.min_val
                        items[-1].max_operator = "<"  # 区间左闭右开，不含上界
        return items

    def build_item(
        self, boundary: _Boundary, price: int
    ) -> ParsedLadderItem:
        return ParsedLadderItem(
            min_val=boundary.min_val,
            min_operator=boundary.min_operator,
            max_val=boundary.max_val,
            max_operator=boundary.max_operator,
            price_adjustment=price,
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
    ) -> int:
        """向下扫描，遇连续 blank_limit 个空行则停。"""
        blank_streak = 0
        for r in range(start_row, max_row + 1):
            has_value = any(
                _to_str(sheet.cell(row=r, column=c).value)
                for c in range(1, max_col + 1)
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
    ) -> int:
        """从 block_end_row 向上回退，去掉末尾空行。"""
        for r in range(block_end_row, header_row, -1):
            if any(
                _to_str(sheet.cell(row=r, column=c).value)
                for c in range(1, max_col + 1)
            ):
                return r
        return header_row

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
        """
        header_row = title_row + header_row_offset
        if header_row > block_end:
            return None

        price_cols = self.collect_price_cols(
            sheet, header_row, start_col=data_col_start, end_col=max_col
        )
        if not price_cols:
            return None

        # 从 header_row + 1 到 block_end，去末尾空行
        data_start = header_row + 1
        data_end = self.trim_block_end(sheet, header_row, block_end, max_col)

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
