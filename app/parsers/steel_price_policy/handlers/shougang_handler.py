"""首钢 Sheet 处理器。

排版特点:
- 厚度块垂直堆叠（冷轧/镀锌），左侧 cols 1-13
- 宽度块跟在厚度块同一行范围的右侧（col 14 起，含宽度标题 "宽度加减价"）

数据布局示例:
    R4: 钢种 厚度加减价,基准厚度1.0——元/吨 ...   冷轧宽度加减价   (col 14)
    R5:        ≤0.5  ≤0.6  ≤0.7 ...               <1500  <1600  ...
    R6: DC01   210   180   140 ...                180    300   ...
"""

from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from .base_handler import BaseSheetHandler
from .constants import GRADE_LABELS


_W_TITLE_COL = 14  # N 列（宽度标题）
_W_DATA_START_COL = 15  # O 列起为宽度边界列
_W_MAX_COL = 18  # 右侧宽度数据列到 R 列


class ShougangSheetHandler(BaseSheetHandler):
    """首钢 Sheet 处理器。"""

    # ------------------------------------------------------------------ #
    # 厚度块：复用基类 locate_thickness_block
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """首钢厚度块与默认布局相同：label_row 在 col 1，max_col=13。"""
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = 13  # 左侧 A-M 列
        last_end = 0

        while True:
            label_rows = self.find_grade_label_rows(sheet, last_end + 1, max_row)
            if not label_rows:
                break
            label_row = label_rows[0]
            if label_row < last_end + 1:
                last_end = label_row
                continue

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

    # ------------------------------------------------------------------ #
    # 宽度块：col 14 出现 "宽度加减价" 标题 → 其下方/同一行 O-R 列为边界列头
    # ------------------------------------------------------------------ #

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = self.col_max(sheet)

        # 找所有 col 14 含"宽度加减价"的标题行
        w_title_rows: List[int] = []
        for r in range(1, max_row + 1):
            text = self.text(sheet, r, _W_TITLE_COL)
            if text and "宽度加减价" in text:
                w_title_rows.append(r)

        for i, title_row in enumerate(w_title_rows):
            block_end = (
                w_title_rows[i + 1] - 1 if i + 1 < len(w_title_rows) else max_row
            )

            # 列头行 = 标题行 + 1（与 magang 宽度块布局一致）
            header_row = title_row + 1
            if header_row > block_end:
                continue

            price_cols = self.collect_price_cols(
                sheet, header_row, start_col=_W_DATA_START_COL, end_col=min(max_col, _W_MAX_COL)
            )
            if not price_cols:
                continue

            title_text = self.text(sheet, title_row, _W_TITLE_COL)
            if "镀锌" in title_text:
                category = "镀锌钢"
            elif "酸洗" in title_text:
                category = "酸洗钢"
            else:
                category = "冷轧钢"

            data_end = self.trim_block_end(sheet, header_row, block_end, max_col)

            blocks.append({
                "category_name": category,
                "policy_type": "WIDTH",
                "grade_col": 1,
                "header_row": header_row,
                "price_cols": price_cols,
                "data_row_start": header_row + 1,
                "data_row_end": data_end,
                "base_thickness": None,
                "grade_blacklist": GRADE_LABELS,
            })

        return blocks