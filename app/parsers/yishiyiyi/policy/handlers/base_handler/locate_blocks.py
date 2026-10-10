"""块定位与边界推断：厚度/宽度块描述、列头边界收集与补全。"""

from __future__ import annotations

import re
from decimal import Decimal

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.boundary_parser import (
    _Boundary,
    _parse_boundary,
    _parse_boundary_thickness,
    is_lte,
    is_strict_gt,
)
from app.parsers.yishiyiyi.policy.handlers.constants import GRADE_LABELS
from app.parsers.yishiyiyi.policy.models.policy_block import PolicyBlock

from .sheet_scanner import SheetScanner

_PURE_NUM_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")


class BlockLocator:
    """厚度 5 步 / 宽度 3 步定位，以及边界收集与上界推断。"""

    def __init__(self, scanner: SheetScanner) -> None:
        self.scanner = scanner

    def locate_thickness_block(
        self,
        sheet: Worksheet,
        label_row: int,
        block_end: int,
    ) -> PolicyBlock | None:
        """执行厚度块的 5 步定位，返回块描述或 None。"""
        title_row = self.scanner.find_thickness_title_row(
            sheet, label_row, block_end, scan_cols=None
        )
        if title_row is None:
            return None

        header_row = self.scanner.find_header_row(sheet, title_row + 1, block_end, scan_cols=None)
        if header_row is None:
            return None

        # header 行遇到第一个空 cell 即终止扫描
        price_cols = self.scanner.collect_price_cols_thickness(sheet, header_row, start_col=2)
        if not price_cols:
            return None

        data_end = block_end
        base_thickness = self.scanner.infer_base_thickness(sheet, header_row, label_row)
        category = self.scanner.infer_category(sheet, label_row)

        return {
            "category_name": category,
            "policy_type": "THICKNESS",
            "grade_col": 1,
            "header_row": header_row,
            "price_cols": price_cols,
            "data_row_start": header_row + 1,
            "data_row_end": data_end,
            "base_thickness": base_thickness,
            "grade_blacklist": GRADE_LABELS,
        }

    def locate_width_block(
        self,
        sheet: Worksheet,
        title_row: int,
        block_end: int,
        grade_col: int,
        data_col_start: int,
        max_col: int,
        *,
        category: str = "冷轧钢",
        header_row_offset: int = 1,
        scan_cols: list[int] | None = None,
    ) -> PolicyBlock | None:
        """执行宽度块的 3 步定位，返回块描述。"""
        del scan_cols
        header_row = title_row + header_row_offset
        if header_row > block_end:
            return None

        price_cols = self.scanner.collect_price_cols(
            sheet, header_row, start_col=data_col_start, end_col=max_col
        )
        if not price_cols:
            return None

        data_start = header_row + 1
        data_end = block_end

        return {
            "category_name": category,
            "policy_type": "WIDTH",
            "grade_col": grade_col,
            "header_row": header_row,
            "price_cols": price_cols,
            "data_row_start": data_start,
            "data_row_end": data_end,
            "base_thickness": None,
            "grade_blacklist": GRADE_LABELS,
        }

    def collect_boundaries(
        self,
        sheet: Worksheet,
        header_row: int,
        price_cols: list[int],
    ) -> dict[int, _Boundary]:
        """从列头行收集所有边界定义（通用版）。"""
        result = {}
        for c in price_cols:
            v = sheet.cell(row=header_row, column=c).value
            b = _parse_boundary(v)
            if b is not None:
                result[c] = b
        return result

    def collect_boundaries_thickness(
        self,
        sheet: Worksheet,
        header_row: int,
        price_cols: list[int],
    ) -> dict[int, _Boundary]:
        """从列头行收集所有边界定义（厚度专用）。

        纯数字（如 "0.5"）规范化为 "<=0.5" 后解析，解析为 min=None, max=数字, max_operator="<="。
        """
        result = {}
        for c in price_cols:
            raw = sheet.cell(row=header_row, column=c).value
            # 纯数字开头：原始数据不规范，补全为 "<=数字" 使其规范
            if isinstance(raw, int | float):
                normalized = "<=" + str(raw)
            elif isinstance(raw, str) and _PURE_NUM_RE.match(raw):
                normalized = "<=" + raw.strip()
            else:
                normalized = str(raw) if raw is not None else ""
            b = _parse_boundary_thickness(normalized)
            if b is not None:
                result[c] = b
        return result

    def infer_upper_bound(
        self,
        boundary: _Boundary,
        sorted_cols: list[int],
        col_idx: int,
        boundaries: dict[int, _Boundary],
        policy_type: str = "WIDTH",
    ) -> _Boundary:
        """推断完整边界：
        1. 厚度第一列纯数字（min=None, max=数字）：隐含 0 < t <= max
        2. 通用第一列（min=None）：min >= 0
        3. 非第一列：从前一列的 max_val 推断 min
        4. 推断上界（见下方逻辑）
        """
        min_val = boundary.min_val
        min_op = boundary.min_operator
        max_val = boundary.max_val
        max_op = boundary.max_operator

        # 1. 推断下界
        if min_val is None:
            if col_idx == 0:
                if policy_type == "THICKNESS" and is_lte(boundary.max_operator):
                    # 厚度纯数字列（如 "0.5"）：隐含 0 < t <= 0.5
                    min_val = Decimal("0")
                    min_op = ">"
                else:
                    # 通用：min >= 0
                    min_val = Decimal("0")
                    min_op = ">="
            else:
                # 从前一列的 max 推断
                prev_c = sorted_cols[col_idx - 1]
                if prev_c in boundaries:
                    prev_boundary = boundaries[prev_c]
                    if prev_boundary.max_val is not None:
                        min_val = prev_boundary.max_val
                        # 操作符：若前一列是 <=，则 min 用 >；若是 <，则 min 用 >=
                        min_op = ">" if is_lte(prev_boundary.max_operator) else ">="

        # 2. 推断上界
        if max_val is None and col_idx < len(sorted_cols) - 1:
            # 有下一列，从下一列的 min_val / min_operator 推断
            # 例：≥1.0 | ＞2.0 → 当前 1.0≤t≤2.0（下一档严格大于，本档闭上界）
            # 例：≥0.9 | ≥1.0 → 当前 0.9≤t<1.0（下一档含等号，本档开上界）
            # 全角/半角（＞/>、≥/>=）均通过 is_strict_gt 识别
            next_c = sorted_cols[col_idx + 1]
            if next_c in boundaries:
                next_boundary = boundaries[next_c]
                if next_boundary.min_val is not None:
                    max_val = next_boundary.min_val
                    max_op = "<=" if is_strict_gt(next_boundary.min_operator) else "<"
        # else: 最后一列且无上界，max_val 保持 None（表示 ∞）

        return _Boundary(
            min_val=min_val,
            min_operator=min_op,
            max_val=max_val,
            max_operator=max_op,
        )
