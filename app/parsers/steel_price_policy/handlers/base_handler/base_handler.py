"""Sheet 处理器基类。

职责：只负责"如何找到块"以及"编排流程"，回归基类本质。
- parse() — 解析入口，编排 find_*_blocks → build_policies_from_block
- find_thickness_blocks / find_width_blocks — 子类覆写，返回块描述
- find_default_thickness_blocks — 通用厚度块扫描（子类复用）
- locate_thickness_block / locate_width_block — 委托给 PolicyAssembler

块描述 = {
    "category_name": str,
    "policy_type": str,          # "THICKNESS" 或 "WIDTH"
    "grade_col": int,            # 钢种列
    "header_row": int,           # 列头行（含 boundary）
    "price_cols": List[int],     # 价格列
    "data_row_start": int,
    "data_row_end": int,
    "base_thickness": Decimal | None,
}
"""

from typing import Any, Dict, List, Optional, Tuple

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.steel_price_policy.boundary_parser import _Boundary
from app.parsers.steel_price_policy.handlers.constants import BLANK_LIMIT, GRADE_LABELS
from app.parsers.steel_price_policy.models.ladder_item import ParsedLadderItem
from .policy_assembler import PolicyAssembler
from .sheet_scanner import SheetScanner


class BaseSheetHandler:
    """Sheet 处理器基类。"""

    def __init__(self):
        # 每个实例创建自己的 scanner 和 assembler，保证线程安全
        self.scanner = SheetScanner()
        self.assembler = PolicyAssembler(scanner=self.scanner)

    def parse(
        self,
        sheet: Worksheet,
        steel_mill: str,
        warnings: List[str],
    ) -> List:
        """解析入口：子类通过 find_thickness_blocks / find_width_blocks 描述块，交 assembler 执行。"""
        policies: List = []
        policies.extend(self._parse_blocks(sheet, steel_mill, "THICKNESS"))
        policies.extend(self._parse_blocks(sheet, steel_mill, "WIDTH"))
        return policies

    # ------------------------------------------------------------------ #
    # 子类需要实现的方法（返回块描述列表）
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """返回本 Sheet 所有厚度块的描述。默认返回空，子类覆写。"""
        return []

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """返回本 Sheet 所有宽度块的描述。默认返回空，子类覆写。"""
        return []

    # ------------------------------------------------------------------ #
    # 子类复用的默认厚度块查找
    # ------------------------------------------------------------------ #

    def find_default_thickness_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        max_col: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """默认厚度块扫描: 多个厚度块在左侧垂直堆叠."""
        blocks: List[Dict[str, Any]] = []
        max_row = self.scanner.row_max(sheet)
        max_col = max_col if max_col is not None else self.scanner.col_max(sheet)
        last_end = 0

        all_label_rows = self.scanner.find_grade_label_rows(sheet, 1, max_row)

        while True:
            label_rows = [lr for lr in all_label_rows if lr > last_end]
            if not label_rows:
                break
            label_row = label_rows[0]
            next_label = label_rows[1] if len(label_rows) > 1 else None
            if next_label is not None:
                block_end = next_label - 1
                # 有下一个标签时：向下扫描找真正的数据结束行（遇空即停）
                # 避免把后续的独立子表（如锌层加价表）错误包含进来
                block_end = self._scan_data_end_row(
                    sheet, label_row + 1, block_end, max_col
                )
            else:
                block_end = self._find_thickness_block_end_with_width_hint(
                    sheet, label_row + 1, max_row, max_col
                )

            if block_end <= label_row + 1:
                last_end = label_row + 1
                continue

            block = self.assembler.locate_thickness_block(
                sheet, label_row, block_end, max_col
            )
            if block:
                block["category_name"] = self.assembler.infer_block_category(
                    sheet, block, max_col=max_col
                )
                blocks.append(block)
                last_end = block["data_row_end"]
            else:
                last_end = label_row + 1

        return blocks

    def _scan_data_end_row(
        self,
        sheet: Worksheet,
        start_row: int,
        max_row: int,
        max_col: int,
        *,
        blank_limit: int = BLANK_LIMIT,
    ) -> int:
        """向下扫描找数据结束行：遇连续空行即停。

        适用场景：块之间有独立子表（如镀锌块的锌层加价表）时，
        应该从厚度数据区向下自然结束，而非向上包含子表。
        """
        blank_streak = 0
        for r in range(start_row, max_row + 1):
            has_value = any(
                self.scanner.text(sheet, r, c)
                for c in range(1, max_col + 1)
            )
            if has_value:
                blank_streak = 0
            else:
                blank_streak += 1
                if blank_streak >= blank_limit:
                    return r - blank_limit
        return max_row

    def _find_thickness_block_end_with_width_hint(
        self,
        sheet: Worksheet,
        start_row: int,
        max_row: int,
        max_col: int,
        *,
        blank_limit: int = BLANK_LIMIT,
    ) -> int:
        """向下扫描块末尾, 但提前停在出现宽度标题的行."""
        blank_streak = 0
        for r in range(start_row, max_row + 1):
            text = self.scanner.text(sheet, r, 1)
            if text and ("宽度加减价" in text or "宽度加价" in text):
                return max(start_row, r - 1)
            has_value = any(
                self.scanner.text(sheet, r, c)
                for c in range(1, max_col + 1)
            )
            blank_streak = 0 if has_value else blank_streak + 1
            if blank_streak >= blank_limit:
                return r - blank_limit
        return max_row

    # ------------------------------------------------------------------ #
    # 块解析（委托给 assembler）
    # ------------------------------------------------------------------ #

    def _parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List:
        """给定块描述列表，执行通用解析。"""
        blocks = (
            self.find_thickness_blocks(sheet, steel_mill)
            if policy_type == "THICKNESS"
            else self.find_width_blocks(sheet, steel_mill)
        )
        policies: List = []
        for block in blocks:
            policies.extend(
                self.assembler.build_policies_from_block(sheet, steel_mill, block)
            )
        return policies

    # ------------------------------------------------------------------ #
    # 组合工具：委托给 assembler（子类可按需覆写）
    # ------------------------------------------------------------------ #

    def locate_thickness_block(
        self,
        sheet: Worksheet,
        label_row: int,
        block_end: int,
        max_col: int,
    ) -> Optional[Dict[str, Any]]:
        """委托给 PolicyAssembler 执行 5 步定位。"""
        return self.assembler.locate_thickness_block(
            sheet, label_row, block_end, max_col
        )

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
        scan_cols: Optional[List[int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """委托给 PolicyAssembler 执行 3 步定位。"""
        return self.assembler.locate_width_block(
            sheet, title_row, block_end, grade_col, data_col_start, max_col,
            category=category, header_row_offset=header_row_offset, scan_cols=scan_cols,
        )

    def collect_price_cols(self, sheet: Worksheet, header_row: int, start_col: int = 2, end_col: Optional[int] = None) -> List[int]:
        return self.scanner.collect_price_cols(sheet, header_row, start_col, end_col)

    def find_block_end_row(self, sheet: Worksheet, start_row: int, max_row: int, max_col: int, *, blank_limit: int = BLANK_LIMIT, scan_cols: Optional[List[int]] = None) -> int:
        return self.scanner.find_block_end_row(sheet, start_row, max_row, max_col, blank_limit=blank_limit, scan_cols=scan_cols)

    def find_grade_label_rows(self, sheet: Worksheet, start_row: int = 1, end_row: Optional[int] = None) -> List[int]:
        return self.scanner.find_grade_label_rows(sheet, start_row, end_row)

    def find_section_break_row(self, sheet: Worksheet, start_row: int, max_row: int, scan_col: int = 1) -> Optional[int]:
        return self.scanner.find_section_break_row(sheet, start_row, max_row, scan_col)

    def find_start_row(self, sheet: Worksheet, r: int, c: int) -> Optional[int]:
        return self.scanner.find_start_row(sheet, r, c)

    def row_max(self, sheet: Worksheet) -> int:
        return self.scanner.row_max(sheet)

    def col_max(self, sheet: Worksheet) -> int:
        return self.scanner.col_max(sheet)

    def text(self, sheet: Worksheet, r: int, c: int) -> str:
        return self.scanner.text(sheet, r, c)

    def text_or_none(self, sheet: Worksheet, r: int, c: int) -> Optional[str]:
        return self.scanner.text_or_none(sheet, r, c)

    def category_from_grade_name(self, grade: str) -> str:
        return self.assembler.category_from_grade_name(grade)

    def infer_block_category(self, sheet: Worksheet, block: Dict[str, Any], *, max_col: int = 14) -> str:
        return self.assembler.infer_block_category(sheet, block, max_col=max_col)

    # ------------------------------------------------------------------ #
    # 子类调用别名（子类用下划线前缀，与旧代码兼容）
    # ------------------------------------------------------------------ #

    def _collect_boundaries(
        self,
        sheet: Worksheet,
        header_row: int,
        price_cols: List[int],
    ) -> Dict[int, _Boundary]:
        return self.assembler.collect_boundaries(sheet, header_row, price_cols)

    def _build_items_for_row(
        self,
        sheet: Worksheet,
        r: int,
        price_cols: List[int],
        boundaries: Dict[int, _Boundary],
        policy_type: str = "THICKNESS",
        sort_order: int = 0,
    ) -> Tuple[List[ParsedLadderItem], Any]:
        return self.assembler.build_items_for_row(
            sheet, r, price_cols, boundaries, policy_type, sort_order
        )

    def _infer_grade_type(self, grade: str, policy_type: str) -> str:
        return self.assembler.infer_grade_type(grade, policy_type)

    def _find_value_above(
        self,
        sheet: Worksheet,
        start_row: int,
        col: int,
        min_row: int = 1,
    ) -> int:
        return self.scanner.find_value_above(sheet, start_row, col, min_row)

    def _parse_one_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
        block: Dict[str, Any],
    ) -> List:
        return self.assembler.build_policies_from_block(sheet, steel_mill, block)

    def _parse_blocks_default(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List:
        """THICKNESS 政策的通用解析（子类复用）。"""
        blocks = (
            self.find_thickness_blocks(sheet, steel_mill)
            if policy_type == "THICKNESS"
            else self.find_width_blocks(sheet, steel_mill)
        )
        policies: List = []
        for block in blocks:
            policies.extend(
                self._parse_one_block(sheet, steel_mill, policy_type, block)
            )
        return policies
