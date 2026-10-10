"""默认厚度块扫描。

从 BaseSheetHandler 拆出，供各钢厂 Handler 复用。
"""

from __future__ import annotations

import re
from typing import TypedDict

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.boundary_parser import _parse_boundary_thickness
from app.parsers.yishiyiyi.policy.handlers.constants import GRADE_LABELS
from app.parsers.yishiyiyi.policy.models.policy_block import PolicyBlock

from .policy_assembler import PolicyAssembler
from .sheet_scanner import SheetScanner

_PURE_NUM_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")
_MAX_LABEL_RE = re.compile(r"^最大\s*(\d+(?:\.\d+)?)?\s*$")


class TitleCell(TypedDict):
    row: int
    col: int
    text: str


class ThicknessBlockFinder:
    """通用厚度加减价块定位。"""

    def __init__(
        self,
        scanner: SheetScanner | None = None,
        assembler: PolicyAssembler | None = None,
    ):
        self.scanner = scanner or SheetScanner()
        self.assembler = assembler or PolicyAssembler(scanner=self.scanner)

    def find_default_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
    ) -> list[PolicyBlock]:
        """默认厚度块扫描：按三步逻辑找块。

        第一步：找到所有含「厚度加减价-基准厚度」或「厚度加减价」的单元格
        第二步：从单元格下一行取出加减价范围（boundary 列头）
        第三步：从单元格左边第一列的下一行取出钢种；钢种单元格为空时块结束
        """
        del steel_mill  # 扫描不依赖钢厂；签名与调用方对齐
        blocks: list[PolicyBlock] = []
        max_row = self.scanner.row_max(sheet)
        max_col = self.scanner.col_max(sheet)

        title_cells: list[TitleCell] = []
        for row in range(1, max_row + 1):
            for col in range(1, max_col + 1):
                text = self.scanner.text(sheet, row, col)
                if text and ("厚度加减价-基准厚度" in text or "厚度加减价" in text):
                    next_row_text = self.scanner.text(sheet, row + 1, col)
                    if next_row_text and (
                        any(symbol in next_row_text for symbol in ["≥", "≤", "＞", "<"])
                        or (
                            next_row_text.strip()[0:1].isdigit() if next_row_text.strip() else False
                        )
                    ):
                        title_cells.append({"row": row, "col": col, "text": text})

        for title_cell in title_cells:
            title_row = int(title_cell["row"])
            title_col = int(title_cell["col"])
            header_row = title_row + 1

            grade_col = title_col - 1
            for check_col in range(1, title_col + 1):
                cell_text = self.scanner.text(sheet, title_row, check_col)
                if cell_text and any(label in cell_text for label in GRADE_LABELS):
                    grade_col = check_col
                    break

            block_end = self._find_block_end(sheet, title_row, grade_col, max_row)
            if block_end <= header_row:
                continue

            start_scan_col = max(2, grade_col + 1)
            price_cols = self._collect_boundary_cols(sheet, header_row, start_scan_col)
            if not price_cols:
                continue

            base_thickness = self.scanner.infer_base_thickness(sheet, header_row, title_row)

            block: PolicyBlock = {
                "category_name": "冷轧钢",
                "policy_type": "THICKNESS",
                "grade_col": grade_col,
                "header_row": header_row,
                "price_cols": price_cols,
                "data_row_start": header_row + 1,
                "data_row_end": block_end,
                "base_thickness": base_thickness,
            }
            block["category_name"] = self.assembler.infer_block_category(sheet, block)
            blocks.append(block)

        return blocks

    def _find_block_end(
        self,
        sheet: Worksheet,
        title_row: int,
        grade_col: int,
        max_row: int,
    ) -> int:
        """从第一个钢种数据行扫描，钢种列为空则块结束。"""
        if grade_col < 1:
            grade_col = 1
        start_scan = title_row + 2
        for row in range(start_scan, max_row + 1):
            grade_text = self.scanner.text(sheet, row, grade_col)
            if not grade_text or grade_text.strip() == "":
                return row - 1
        return max_row

    def _collect_boundary_cols(
        self,
        sheet: Worksheet,
        header_row: int,
        title_col: int,
    ) -> list[int]:
        """从 header_row 收集含 boundary 的列。

        厚度块专用：纯数字规范化为「<=数字」后判断。
        扫描遇到第一个空 cell 即终止。
        """
        scan_end = self.scanner.col_max(sheet)
        cols: list[int] = []
        for col in range(title_col, scan_end + 1):
            raw = sheet.cell(row=header_row, column=col).value
            if raw is None:
                break
            raw_stripped = str(raw).strip()
            if _MAX_LABEL_RE.match(raw_stripped):
                cols.append(col)
                continue
            if isinstance(raw, int | float):
                normalized = "<=" + str(raw)
            elif isinstance(raw, str):
                match = _MAX_LABEL_RE.match(raw_stripped)
                if match and match.group(1):
                    normalized = "<= " + match.group(1)
                elif _PURE_NUM_RE.match(raw_stripped):
                    normalized = "<=" + raw_stripped
                else:
                    normalized = raw_stripped
            else:
                normalized = str(raw)
            if _parse_boundary_thickness(normalized) is not None:
                cols.append(col)
        return cols
