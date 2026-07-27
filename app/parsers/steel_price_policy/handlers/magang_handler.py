"""马钢 Sheet 处理器。

排版特点:
- 左侧（cols 1-14）：厚度块，多个垂直堆叠
- 右侧（cols 15+）：宽度块，多个垂直堆叠
"""
from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from .base_handler import BaseSheetHandler
from .constants import GRADE_LABELS


# 马钢右侧宽度块
_W_GRADE_COL = 15
_W_START_COL = 16


class MagangSheetHandler(BaseSheetHandler):
    """马钢 Sheet 处理器。"""

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        max_row, max_col = self.row_max(sheet), 14
        last_end = 0

        while True:
            label_rows = self.find_grade_label_rows(sheet, last_end + 1, max_row)
            if not label_rows:
                break
            label_row = label_rows[0]

            block_end = self.find_block_end_row(sheet, label_row + 1, max_row, max_col)
            if block_end <= label_row + 1:
                last_end = label_row + 1
                continue

            block = self.locate_thickness_block(sheet, label_row, block_end, max_col)
            if block:
                blocks.append(block)
                last_end = block["data_row_end"]
            else:
                last_end = label_row + 1

        return blocks

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        max_row, max_col = self.row_max(sheet), self.col_max(sheet)

        if max_col < _W_START_COL:
            return []

        w_title_rows: List[int] = []
        for r in range(1, max_row + 1):
            for c in range(_W_START_COL, max_col + 1):
                text = self.text(sheet, r, c)
                if "宽度W(mm)" in text or "宽度(mm)" in text or text == "宽度W":
                    w_title_rows.append(r)
                    break

        for i, title_row in enumerate(w_title_rows):
            block_end = w_title_rows[i + 1] - 1 if i + 1 < len(w_title_rows) else max_row

            block = self.locate_width_block(
                sheet, title_row, block_end,
                grade_col=_W_GRADE_COL, data_col_start=_W_START_COL, max_col=max_col,
                category="冷轧钢",
                header_row_offset=1,
            )
            if block:
                blocks.append(block)

        return blocks
