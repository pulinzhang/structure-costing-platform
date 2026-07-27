"""鞍钢集团 Sheet 处理器。

排版特点:
- 左侧（cols 1-10）：单一厚度块，共用 header
- 右侧（cols 17+）：3 个宽度子块（冷轧/镀锌/酸洗），
  每块从标题行（含类别关键字）开始，到下一个类别标题 - 1

复用基类的 locate_thickness_block 处理左侧厚度，
find_width_blocks 处理右侧 3 个宽度块。
"""
from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from .base_handler import BaseSheetHandler
from .constants import GRADE_LABELS


# 鞍钢集团宽度块：标题列 = 17（Q 列），列头行 = 标题行 + 1
_W_TITLE_COL = 17
_W_HEADER_COL = 17  # "宽度mm" 在 title_row 的同一列
_CATEGORY_KEYWORDS = (
    ("冷轧产品", "冷轧钢"),
    ("镀锌产品", "镀锌钢"),
    ("酸洗产品", "酸洗钢"),
)


class AngangSheetHandler(BaseSheetHandler):
    """鞍钢集团 Sheet 处理器。"""

    # ------------------------------------------------------------------ #
    # 厚度块
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """左侧（cols 1-10）：单一厚度块。"""
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = 10  # 左侧厚度只到 J 列

        label_rows = self.find_grade_label_rows(sheet, 1, max_row)
        if not label_rows:
            return []

        label_row = label_rows[0]
        block_end = self.find_block_end_row(
            sheet, label_row + 1, max_row, max_col
        )

        block = self.locate_thickness_block(
            sheet, label_row, block_end, max_col
        )
        if block:
            blocks.append(block)

        return blocks

    # ------------------------------------------------------------------ #
    # 宽度块
    # ------------------------------------------------------------------ #

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """右侧（cols 17+）：3 个宽度子块（冷轧/镀锌/酸洗）。

        标题在 col 17（R4=`冷轧产品宽度加价`，R8=`镀锌...`，R12=`酸洗...`）。
        列头行 = 标题行 + 1，列头列 = 17。
        """
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = self.col_max(sheet)

        # 收集所有宽度块起始行（col 17 含"宽度加价"）
        block_starts: List[int] = []
        for r in range(1, max_row + 1):
            text = self.text(sheet, r, _W_TITLE_COL)
            if text and "宽度" in text and "加价" in text:
                block_starts.append(r)

        for i, title_row in enumerate(block_starts):
            # 该块结束 = 下一个块标题 - 1
            block_end = (
                block_starts[i + 1] - 1 if i + 1 < len(block_starts) else max_row
            )

            # 列头行 = 标题行 + 1
            header_row = title_row + 1
            if header_row > block_end:
                continue

            # 推断 category
            title_text = self.text(sheet, title_row, _W_TITLE_COL)
            category = "冷轧钢"
            for kw, cat in _CATEGORY_KEYWORDS:
                if kw in title_text:
                    category = cat
                    break

            # 宽度边界列（从 col 18 起）
            price_cols = self.collect_price_cols(
                sheet, header_row, start_col=_W_HEADER_COL + 1, end_col=max_col
            )
            if not price_cols:
                continue

            blocks.append({
                "category_name": category,
                "policy_type": "WIDTH",
                "grade_col": 1,
                "header_row": header_row,
                "price_cols": price_cols,
                "data_row_start": header_row + 1,
                "data_row_end": block_end,
                "base_thickness": None,
                "grade_blacklist": GRADE_LABELS,
            })

        return blocks
