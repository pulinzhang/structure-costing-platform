"""VAMA Sheet 处理器。

排版特点:
- 厚度块垂直堆叠（冷轧/镀锌）
- 右侧独立宽度块（col 10 以后，`宽度(mm)` 标题列起）
"""
from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from .base_handler import BaseSheetHandler
from .constants import GRADE_LABELS


class VamaSheetHandler(BaseSheetHandler):
    """VAMA Sheet 处理器。"""

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        return self.find_default_thickness_blocks(sheet, steel_mill)

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        max_row, max_col = self.row_max(sheet), self.col_max(sheet)

        # 找所有 `宽度(mm)` / `宽度W` 标题行
        w_title_rows: List[int] = []
        for r in range(1, max_row + 1):
            for c in range(1, max_col + 1):
                text = self.text(sheet, r, c)
                if "宽度(mm)" in text or "宽度W" in text:
                    w_title_rows.append(r)
                    break

        for i, title_row in enumerate(w_title_rows):
            block_end = w_title_rows[i + 1] - 1 if i + 1 < len(w_title_rows) else max_row
            # 找列头行（需扫描 col 11 以右找 boundary）
            header_row = self.find_header_row(
                sheet, title_row + 1, block_end,
                scan_cols=list(range(11, max_col + 1))
            )
            if header_row is None:
                continue

            price_cols = self.collect_price_cols(sheet, header_row, start_col=11, end_col=max_col)
            if not price_cols:
                continue

            data_start = header_row + 1
            data_end = self.trim_block_end(sheet, header_row, block_end, max_col)

            blocks.append({
                "category_name": "冷轧钢",
                "policy_type": "WIDTH",
                "grade_col": 1,
                "header_row": header_row,
                "price_cols": price_cols,
                "data_row_start": data_start,
                "data_row_end": data_end,
                "base_thickness": None,
                "grade_blacklist": GRADE_LABELS,
            })

        return blocks
