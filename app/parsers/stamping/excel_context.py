"""
Excel 上下文模块

负责：
- Sheet 查找
- 零件号列合并单元格缓存
- 单元格值获取
"""

from typing import Any, List, Optional

import openpyxl

from app.utils.logging_config import get_logger
from app.parsers.stamping.models.part_no_range import PartNoRange


logger = get_logger("parser.stamping.excel")


class ExcelContext:
    """Excel 工作表上下文"""

    def __init__(self) -> None:
        self.workbook: Optional[openpyxl.Workbook] = None
        self.sheet: Optional[openpyxl.worksheet.worksheet.Worksheet] = None
        self.max_row: int = 0
        self.max_column: int = 0
        # 零件号合并范围列表（按 start_row 排序）
        self._part_no_ranges: List[PartNoRange] = []

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
            if not self.sheet:
                self.sheet = self.workbook.active

        if self.sheet is None:
            raise ValueError("未找到可用 Sheet")

        self.max_row = self.sheet.max_row
        self.max_column = self.sheet.max_column
        return self.sheet

    def _find_stamping_sheet(self) -> Optional[openpyxl.worksheet.worksheet.Worksheet]:
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
        建立零件号列的合并单元格缓存。

        Args:
            part_no_col: 零件号列号（1-based）
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

            self._part_no_ranges.append(PartNoRange(
                value=value,
                start_row=min_r,
                end_row=max_r,
            ))

        # 按起始行排序
        self._part_no_ranges.sort(key=lambda x: x.start_row)
        logger.info(f"零件号合并范围: {len(self._part_no_ranges)} 个")

    def get_part_no_range(self, row: int) -> Optional[PartNoRange]:
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
        """获取单元格值"""
        if self.sheet is None:
            return None
        return self.sheet.cell(row, col).value

    def close(self) -> None:
        """关闭工作簿"""
        if self.workbook:
            self.workbook.close()
            self.workbook = None
            self.sheet = None
