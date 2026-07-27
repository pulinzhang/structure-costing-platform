"""通用默认 Sheet 处理器。

适用排版：多个厚度块垂直堆叠（冷轧 / 镀锌 / 酸洗）。
子类只需覆写 find_thickness_blocks / find_width_blocks，
基类负责块 → ParsedPolicy 的通用解析。

块结构:
    [钢种列]  [厚度列1] [厚度列2] ... [厚度列N]
    DC01       180       140       ...
"""

from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from .base_handler import BaseSheetHandler


class DefaultSheetHandler(BaseSheetHandler):
    """默认 Sheet 处理器（厚度块垂直堆叠）。"""

    # ------------------------------------------------------------------ #
    # 厚度块查找
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = self.col_max(sheet)
        last_end = 0

        for r in range(1, max_row + 1):
            if r <= last_end:
                continue
            # 找下一个钢种标签行
            label_rows = self.find_grade_label_rows(sheet, r, max_row)
            if not label_rows:
                break
            label_row = label_rows[0]
            if label_row < r:
                continue

            block_end = self.find_block_end_row(
                sheet, label_row + 1, max_row, max_col
            )
            if block_end <= label_row + 1:
                last_end = label_row + 1
                continue

            block = self.locate_thickness_block(
                sheet, label_row, block_end, max_col
            )
            if block:
                blocks.append(block)
                last_end = block["data_row_end"]
        return blocks

    # ------------------------------------------------------------------ #
    # 宽度块查找（默认无）
    # ------------------------------------------------------------------ #

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        return []
