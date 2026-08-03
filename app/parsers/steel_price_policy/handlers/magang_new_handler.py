"""马钢 Sheet 处理器。

排版特点:
- 左侧（cols 1-14）：厚度块，多个垂直堆叠
- 右侧（cols 15+）：宽度块，多个垂直堆叠

分类推断:
- 马钢(新) 的 sheet 不在标题里写明"冷轧钢/镀锌钢"字面,仅靠钢种名后缀区分:
    +Z  → 镀锌钢
    其它 → 冷轧钢 (默认)
"""
from typing import Any, Dict, List, Optional

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.steel_price_policy.handlers.base_handler import BaseSheetHandler


# 马钢右侧宽度块
_W_GRADE_COL = 15
_W_START_COL = 16


class MagangNewSheetHandler(BaseSheetHandler):
    """马钢 Sheet 处理器。"""

    def find_last_label_row_in_range(
        self,
        sheet: Worksheet,
        start_row: int,
        end_row: int,
        label_col: int,
    ) -> Optional[int]:
        """在 [start_row, end_row] 范围内，从后向前找钢种列最后一个有值的行。

        考虑合并单元格：若某行在合并区域内，即使该行自身值为 None，
        也视为有值（因为其值来自合并区域的起始单元格）。
        """
        for r in range(end_row, start_row - 1, -1):
            raw_val = sheet.cell(row=r, column=label_col).value
            if raw_val is not None:
                return r
            # 值为 None，检查是否在合并单元格区域内
            if self.find_start_row(sheet, r, label_col) is not None:
                return r
        return None

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        max_row, max_col = self.row_max(sheet), 14
        last_end = 0

        # 预先找所有 label_row, 用作块天然边界
        all_label_rows = self.find_grade_label_rows(sheet, 1, max_row)

        while True:
            # 从 last_end + 1 之后找下一个 label_row (天然块边界)
            label_rows = [lr for lr in all_label_rows if lr > last_end]
            if not label_rows:
                break
            label_row = label_rows[0]
            # 本块的 label_row 在 last_end + 1 与下个 label_row 之间
            # 取下个 label_row (label_rows[1] if exists) 作为 block_end
            next_label = label_rows[1] if len(label_rows) > 1 else None
            # 有下一个 label 时，find_block_end_row 的 end_row 用 min(下个label-1, max_row)
            # 即只在本块列范围内扫描，避免跨到下个块
            scan_end = min(next_label - 1, max_row) if next_label else max_row
            block_end = self.find_block_end_row(
                sheet, label_row + 1, scan_end, max_col,
            )
            if next_label:
                block_end = min(block_end, next_label - 1)
            if block_end <= label_row + 1:
                last_end = label_row + 1
                continue

            block = self.locate_thickness_block(sheet, label_row, block_end, max_col)
            if block:
                # 按本块实际钢种名后缀推断 category（复用 assembler 的推断逻辑）
                block["category_name"] = self.assembler.infer_block_category(
                    sheet, block, max_col=max_col
                )
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

        # 只扫描右侧列区域（col 15+）的 label 行，作为块天然边界
        w_title_rows: List[int] = []
        for r in range(1, max_row + 1):
            for c in range(_W_START_COL, max_col + 1):
                text = self.text(sheet, r, c)
                if "宽度W(mm)" in text or "宽度(mm)" in text or text == "宽度W":
                    w_title_rows.append(r)
                    break

        # 用完即弃的独立扫描器，不污染 last_end
        # scan_cols 仅含价格列（排除钢种列），用于价格数据扫描
        # 钢种列单独处理，用合并单元格信息确定结束行
        w_scan_cols = list(range(_W_START_COL + 1, max_col + 1))  # 价格列，从 col 16 起

        for i, title_row in enumerate(w_title_rows):
            # 找本块钢种列（col 15）的最后一个非空行
            # candidate_end 限制为本块范围：下一个 title_row - 1（若有），否则 max_row
            candidate_start = title_row + 1
            if i + 1 < len(w_title_rows):
                candidate_end = w_title_rows[i + 1] - 1
            else:
                candidate_end = max_row
            last_grade_row = self.find_last_label_row_in_range(
                sheet, candidate_start, candidate_end, _W_GRADE_COL,
            )
            if last_grade_row is None:
                continue
            block_end = last_grade_row

            if block_end <= title_row + 1:
                continue

            block = self.locate_width_block(
                sheet, title_row, block_end,
                grade_col=_W_GRADE_COL, data_col_start=_W_START_COL, max_col=max_col,
                category="冷轧钢",
                header_row_offset=1,
                scan_cols=w_scan_cols,
            )
            if block:
                # 按本块实际钢种名后缀推断 category（复用 assembler 的推断逻辑）
                block["category_name"] = self.assembler.infer_block_category(
                    sheet, block, max_col=max_col
                )
                blocks.append(block)

        return blocks
