"""
Excel 上下文模块

负责：
- Sheet 查找
- 零件号列合并单元格缓存
- 单元格值获取
"""

from typing import Any

import openpyxl

from app.common.part_number import looks_like_part_number_cell
from app.parsers.stamping.models.part_no_range import PartNoRange
from app.utils.logging_config import get_logger

logger = get_logger("parser.stamping.excel")


class ExcelContext:
    """Excel 工作表上下文"""

    def __init__(self) -> None:
        self.workbook: openpyxl.Workbook | None = None
        self.sheet: openpyxl.worksheet.worksheet.Worksheet | None = None
        self.max_row: int = 0
        self.max_column: int = 0
        # 零件号合并范围列表（按 start_row 排序）
        self._part_no_ranges: list[PartNoRange] = []
        # 任意合并区：(row, col) → 左上角 (row, col)；表头探测仍走 get_value 避免串列
        self._merge_origin: dict[tuple[int, int], tuple[int, int]] = {}

    def load(self, file_path: str) -> None:
        """加载 Excel 文件"""
        self.workbook = openpyxl.load_workbook(file_path, data_only=True)
        self.max_row = 0
        self.max_column = 0

    def find_sheet(self, sheet_title: str | None = None) -> openpyxl.worksheet.worksheet.Worksheet:
        """查找指定 Sheet 或自动识别"""
        if self.workbook is None:
            raise ValueError("Workbook not loaded")

        if sheet_title:
            self.sheet = self.workbook[sheet_title]
        else:
            self.sheet = self._find_stamping_sheet()
            if self.sheet is None and self.workbook.worksheets:
                self.sheet = self.workbook.worksheets[0]

        if self.sheet is None:
            raise ValueError("未找到可用 Sheet")

        self.max_row = self.sheet.max_row
        self.max_column = self.sheet.max_column
        self._build_merge_origin_cache()
        return self.sheet

    def _build_merge_origin_cache(self) -> None:
        """记录每个合并区内格子对应的左上角，供 get_merged_value 使用。"""
        self._merge_origin = {}
        if self.sheet is None:
            return
        for merged_range in self.sheet.merged_cells.ranges:
            origin = (merged_range.min_row, merged_range.min_col)
            for row in range(merged_range.min_row, merged_range.max_row + 1):
                for col in range(merged_range.min_col, merged_range.max_col + 1):
                    self._merge_origin[(row, col)] = origin

    def _find_stamping_sheet(self) -> openpyxl.worksheet.worksheet.Worksheet | None:
        """识别冲压数据Sheet"""
        for sheet in self.workbook.worksheets:
            for row_idx in range(1, min(16, sheet.max_row + 1)):
                row_values = [self.get_value(row_idx, col) for col in range(1, 25)]
                row_text = " ".join([str(v) for v in row_values if v])

                has_part = any(p in row_text for p in ["零件号", "件号", "Part No"])
                has_op = any(p in row_text for p in ["工序", "OP", "Process"])

                if has_part and has_op:
                    logger.info(f"找到数据Sheet: {sheet.title}, 行{row_idx}")
                    return sheet
        return None

    def build_merged_cache(self, part_no_col: int) -> None:
        """
        建立零件号列的范围缓存。

        先收录零件号列上的纵向合并；再把未合并、非表头的单格零件号做成一行一段
        （工程变更常只写一道工序，不像 SOP 样表那样整段合并）。
        """
        if self.sheet is None:
            return

        self._part_no_ranges = []
        for merged_range in self.sheet.merged_cells.ranges:
            min_c = merged_range.min_col
            max_c = merged_range.max_col

            # 只处理零件号列
            if min_c != part_no_col or max_c != part_no_col:
                continue

            min_r = merged_range.min_row
            max_r = merged_range.max_row
            value = self.sheet.cell(min_r, min_c).value
            if not looks_like_part_number_cell(value):
                continue

            self._part_no_ranges.append(
                PartNoRange(
                    value=value,
                    start_row=min_r,
                    end_row=max_r,
                )
            )

        covered_rows = {
            row
            for part_range in self._part_no_ranges
            for row in range(part_range.start_row, part_range.end_row + 1)
        }
        for row in range(1, (self.max_row or 0) + 1):
            if row in covered_rows:
                continue
            value = self.sheet.cell(row, part_no_col).value
            if not looks_like_part_number_cell(value):
                continue
            self._part_no_ranges.append(PartNoRange(value=value, start_row=row, end_row=row))

        # 按起始行排序
        self._part_no_ranges.sort(key=lambda x: x.start_row)
        logger.info(f"零件号合并范围: {len(self._part_no_ranges)} 个")

    def get_part_no_range(self, row: int) -> PartNoRange | None:
        """
        获取指定行所属的零件号范围。

        Returns:
            该行所属的 PartNoRange，如不在任何合并范围内则返回 None
        """
        for pr in self._part_no_ranges:
            if pr.contains(row):
                return pr
        return None

    def get_value(self, row: int, col: int) -> Any:
        """读取该格自身的值，不解析合并区（表头列映射依赖此行为）。"""
        if self.sheet is None:
            return None
        return self.sheet.cell(row, col).value

    def get_merged_value(self, row: int, col: int) -> Any:
        """读取合并区左上角的值；未合并则等同 get_value。"""
        if self.sheet is None:
            return None
        origin_row, origin_col = self._merge_origin.get((row, col), (row, col))
        return self.sheet.cell(origin_row, origin_col).value

    def close(self) -> None:
        """关闭工作簿"""
        if self.workbook:
            self.workbook.close()
            self.workbook = None
            self.sheet = None
            self._merge_origin = {}
            self._part_no_ranges = []
