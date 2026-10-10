"""SheetScanner：封装所有与 openpyxl 交互的"脏活累活"。

职责：
- 单元格读写（cell / text / text_or_none）
- 维度探测（row_max / col_max）
- 合并单元格处理（find_start_row / find_value_above_with_row）
- 搜索定位（find_grade_label_rows / find_header_row / find_block_end_row）
- 收集（collect_price_cols）

所有方法签名均为 (sheet: Worksheet, ...) → 纯数据，不含业务语义。
"""

from decimal import Decimal
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.boundary_parser import _parse_boundary
from app.parsers.yishiyiyi.policy.handlers.constants import (
    BENCH_PATTERN,
    BLANK_LIMIT,
    GRADE_LABELS,
    THICKNESS_HEADER_KEYWORDS,
)
from app.parsers.yishiyiyi.policy.value_parser import _to_int_price, _to_str, _to_str_or_none


class SheetScanner:
    """Sheet 扫描仪：封装所有 openpyxl 原语操作。"""

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
    def text_or_none(sheet: Worksheet, r: int, c: int) -> str | None:
        return _to_str_or_none(sheet.cell(row=r, column=c).value)

    @staticmethod
    def row_max(sheet: Worksheet) -> int:
        return sheet.max_row or 0

    @staticmethod
    def col_max(sheet: Worksheet) -> int:
        return sheet.max_column or 0

    # ------------------------------------------------------------------ #
    # 合并单元格工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def find_start_row(
        sheet: Worksheet,
        r: int,
        c: int,
    ) -> int | None:
        """检查单元格是否在合并区域内，如果是，返回合并区域的起始行号。

        在 openpyxl 中，合并单元格的起始单元格（top-left cell）存储值，
        其他被合并的单元格值为 None。
        """
        for merged_range in sheet.merged_cells:
            min_row = merged_range.min_row
            max_row = merged_range.max_row
            min_col = merged_range.min_col
            max_col = merged_range.max_col
            if min_row is None or max_row is None or min_col is None or max_col is None:
                continue
            if min_row <= r <= max_row and min_col <= c <= max_col:
                return int(min_row)
        return None

    @staticmethod
    def find_value_above_with_row(
        sheet: Worksheet,
        start_row: int,
        col: int,
        min_row: int = 1,
    ) -> tuple[int, int]:
        """向上查找最近的非 None 整数值，同时返回 (price, actual_row)。

        用于溯源：保证 excel_row 与 price_adjustment 所在单元格严格对齐。
        """
        for r in range(start_row - 1, min_row - 1, -1):
            val = sheet.cell(row=r, column=col).value
            if val is not None:
                return _to_int_price(val), r
        return 0, start_row

    # ------------------------------------------------------------------ #
    # 搜索定位
    # ------------------------------------------------------------------ #

    def find_grade_label_rows(
        self,
        sheet: Worksheet,
        start_row: int = 1,
        end_row: int | None = None,
    ) -> list[int]:
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
        scan_cols: list[int] | None = None,
    ) -> int | None:
        """在 start_row ~ end_row 内找首个含厚度关键字的行。"""
        max_col = scan_cols[-1] if scan_cols else self.col_max(sheet)
        for r in range(start_row, min(start_row + 5, end_row + 1)):
            for c in scan_cols or range(1, max_col + 1):
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
        scan_cols: list[int] | None = None,
    ) -> int | None:
        """在 start_row ~ end_row 内找首个含 boundary 的行（列头行）。"""
        max_col = scan_cols[-1] if scan_cols else self.col_max(sheet)
        for r in range(start_row, min(start_row + 5, end_row + 1)):
            for c in scan_cols or range(1, max_col + 1):
                if _parse_boundary(sheet.cell(row=r, column=c).value) is not None:
                    return r
        return None

    def collect_price_cols(
        self,
        sheet: Worksheet,
        header_row: int,
        start_col: int = 2,
        end_col: int | None = None,
    ) -> list[int]:
        """在 header_row 上收集所有含 boundary 的列（通用版）。"""
        end_col = end_col or self.col_max(sheet)
        cols = []
        for c in range(start_col, end_col + 1):
            if _parse_boundary(sheet.cell(row=header_row, column=c).value) is not None:
                cols.append(c)
        return cols

    def collect_price_cols_thickness(
        self,
        sheet: Worksheet,
        header_row: int,
        start_col: int = 2,
        end_col: int | None = None,
    ) -> list[int]:
        """在 header_row 上收集所有含 boundary 的列（厚度专用版）。

        纯数字规范化为 "<=数字" 后判断，如 "0.5" → <=0.5。
        扫描时遇到第一个空 cell 即终止（块的边界由单元格是否为空决定）。
        例如：0.5  ＞0.5  ≥0.6  ≥0.7  ≥0.8  ≥1.0  ≥1.5  ≥1.8  ≥2.3  ≥2.51
        当某列的单元格为空时，其后的列不再属于该块。
        """
        import re

        from app.parsers.yishiyiyi.policy.boundary_parser import _parse_boundary_thickness

        _PURE_NUM_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")
        scan_end = end_col if end_col is not None else self.col_max(sheet)
        cols = []
        for c in range(start_col, scan_end + 1):
            raw = sheet.cell(row=header_row, column=c).value
            if raw is None:
                break
            if isinstance(raw, int | float):
                normalized = "<=" + str(raw)
            elif isinstance(raw, str) and _PURE_NUM_RE.match(raw):
                normalized = "<=" + raw.strip()
            else:
                normalized = str(raw)
            if _parse_boundary_thickness(normalized) is not None:
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
        scan_cols: list[int] | None = None,
    ) -> int:
        """向下扫描，遇连续 blank_limit 个空行则停。"""
        blank_streak = 0
        cols = scan_cols if scan_cols is not None else list(range(1, max_col + 1))
        for r in range(start_row, max_row + 1):
            has_value = any(_to_str(sheet.cell(row=r, column=c).value) for c in cols)
            blank_streak = 0 if has_value else blank_streak + 1
            if blank_streak >= blank_limit:
                return r - blank_limit
        return max_row

    # ------------------------------------------------------------------ #
    # 边界信号
    # ------------------------------------------------------------------ #

    _SECTION_BREAK_KEYWORDS: tuple[str, ...] = (
        "厚度加减价",
        "厚度(mm)",
        "厚度（mm）",
        "宽度加减价",
        "宽度加价",
        "宽度(mm)",
        "宽度（mm）",
    )

    def find_section_break_row(
        self,
        sheet: Worksheet,
        start_row: int,
        max_row: int,
        scan_col: int = 1,
    ) -> int | None:
        """从 start_row 起向下扫描，找到第一个"段标题"行（新块开始）。"""
        for r in range(start_row, max_row + 1):
            text = self.text(sheet, r, scan_col)
            if not text:
                continue
            for kw in self._SECTION_BREAK_KEYWORDS:
                if kw in text:
                    return r
        return None

    # ------------------------------------------------------------------ #
    # 推断（不涉及业务语义，仅从文本提取信息）
    # ------------------------------------------------------------------ #

    def infer_base_thickness(
        self,
        sheet: Worksheet,
        header_row: int,
        label_row: int,
    ) -> Decimal | None:
        """在 header_row 附近（向上 3 行）查找 `基准厚度 X.X`。"""
        scan_end = self.col_max(sheet)
        for r in range(max(1, label_row - 3), header_row + 1):
            for c in range(1, scan_end + 1):
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
    ) -> str:
        """在 label_row 上方 6 行内查找分类关键字。"""
        from app.parsers.yishiyiyi.policy.handlers.constants import CATEGORY_HINTS

        scan_end = self.col_max(sheet)
        for r in range(max(1, label_row - 6), label_row):
            for c in range(1, scan_end + 1):
                text = _to_str(sheet.cell(row=r, column=c).value)
                if not text:
                    continue
                for hint in CATEGORY_HINTS:
                    if hint in text:
                        return hint
        return "冷轧钢"
