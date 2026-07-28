"""唐钢 Sheet 处理器。

排版特点:
- 顶部：厚度块垂直堆叠（冷轧/镀锌）
- 底部：多个宽度块（A 列起标题，如"冷轧宽度加价"、"镀锌宽度加价"）
"""
from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from .base_handler import BaseSheetHandler
from .constants import GRADE_LABELS


class TanggangSheetHandler(BaseSheetHandler):
    """唐钢 Sheet 处理器。"""

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        return self.find_default_thickness_blocks(sheet, steel_mill)

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        max_row, max_col = self.row_max(sheet), self.col_max(sheet)

        w_title_rows: List[int] = []
        for r in range(1, max_row + 1):
            text = self.text(sheet, r, 1)
            if text and ("宽度加价" in text or "宽度加减价" in text):
                w_title_rows.append(r)

        for i, title_row in enumerate(w_title_rows):
            if i + 1 < len(w_title_rows):
                block_end = w_title_rows[i + 1] - 1
            else:
                block_end = self.find_block_end_row(
                    sheet, title_row + 2, max_row, max_col
                )
            # 避免吸入后面的"钢种"/"厚度加减价" label_row 或段标题
            next_label_rows = self.find_grade_label_rows(sheet, title_row + 2, max_row)
            if next_label_rows:
                block_end = min(block_end, next_label_rows[0] - 1)
            next_break = self.find_section_break_row(
                sheet, title_row + 2, max_row, scan_col=1
            )
            if next_break is not None:
                block_end = min(block_end, next_break - 1)
            title_text = self.text(sheet, title_row, 1)
            if "镀锌" in title_text:
                category = "镀锌钢"
            elif "酸洗" in title_text:
                category = "酸洗钢"
            else:
                category = "冷轧钢"

            block = self.locate_width_block(
                sheet, title_row, block_end,
                grade_col=1, data_col_start=2, max_col=max_col,
                category=category,
            )
            if block:
                blocks.append(block)

        return blocks
