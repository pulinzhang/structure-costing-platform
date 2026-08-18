"""Sheet 处理器基类。

职责：编排 parse 流程 + 暴露子类钩子；具体表解析委托给专用组件。
- ZincCoatingParser — 锌层加价
- ThicknessBlockFinder — 默认厚度块扫描
- PolicyAssembler / SheetScanner — 语义装配与单元格读取

块描述 = {
    "category_name": str,
    "policy_type": str,          # "THICKNESS" 或 "WIDTH"
    "grade_col": int,
    "header_row": int,
    "price_cols": List[int],
    "data_row_start": int,
    "data_row_end": int,
    "base_thickness": Decimal | None,
}
"""

from typing import Any, Dict, List, Optional, Tuple

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.boundary_parser import _Boundary
from app.parsers.yishiyiyi.policy.handlers.constants import BLANK_LIMIT
from app.parsers.yishiyiyi.policy.models import ParsedPolicy
from app.parsers.yishiyiyi.policy.models.ladder_item import ParsedLadderItem
from .policy_assembler import PolicyAssembler
from .sheet_scanner import SheetScanner
from .thickness_block_finder import ThicknessBlockFinder
from .zinc_coating import ZincCoatingParser


class BaseSheetHandler:
    """Sheet 处理器基类：只做编排与钩子，不做专用表解析。"""

    def __init__(self) -> None:
        # 每个实例自有 scanner/assembler，保证线程安全
        self.scanner = SheetScanner()
        self.assembler = PolicyAssembler(scanner=self.scanner)
        self._zinc_parser = ZincCoatingParser(scanner=self.scanner)
        self._thickness_finder = ThicknessBlockFinder(
            scanner=self.scanner,
            assembler=self.assembler,
        )

    def parse(
        self,
        sheet: Worksheet,
        steel_mill: str,
        warnings: List[str],
    ) -> List[ParsedPolicy]:
        """解析入口：厚度块 + 宽度块 + 锌层加价块。"""
        del warnings
        policies: List[ParsedPolicy] = []
        policies.extend(self._parse_blocks(sheet, steel_mill, "THICKNESS"))
        policies.extend(self._parse_blocks(sheet, steel_mill, "WIDTH"))
        policies.extend(self.parse_zinc_coating_blocks(sheet, steel_mill))
        return policies

    # ------------------------------------------------------------------ #
    # 子类钩子
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """返回本 Sheet 所有厚度块描述。默认空，子类覆写。"""
        return []

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """返回本 Sheet 所有宽度块描述。默认空，子类覆写。"""
        return []

    # ------------------------------------------------------------------ #
    # 复用组件（对外 API 保持不变，内部委托）
    # ------------------------------------------------------------------ #

    def find_zinc_coating_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        return self._zinc_parser.find_blocks(sheet, steel_mill)

    def parse_zinc_coating_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[ParsedPolicy]:
        return self._zinc_parser.parse_blocks(sheet, steel_mill)

    def find_default_thickness_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
    ) -> List[Dict[str, Any]]:
        return self._thickness_finder.find_default_blocks(sheet, steel_mill)

    # ------------------------------------------------------------------ #
    # 块解析编排
    # ------------------------------------------------------------------ #

    def _parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List[ParsedPolicy]:
        """按块描述列表执行通用解析。"""
        blocks = (
            self.find_thickness_blocks(sheet, steel_mill)
            if policy_type == "THICKNESS"
            else self.find_width_blocks(sheet, steel_mill)
        )
        policies: List[ParsedPolicy] = []
        for block in blocks:
            policies.extend(
                self.assembler.build_policies_from_block(sheet, steel_mill, block)
            )
        return policies

    def _parse_one_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
        block: Dict[str, Any],
    ) -> List[ParsedPolicy]:
        del policy_type
        return self.assembler.build_policies_from_block(sheet, steel_mill, block)

    def _parse_blocks_default(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List[ParsedPolicy]:
        """THICKNESS/WIDTH 通用解析（子类复用）。"""
        blocks = (
            self.find_thickness_blocks(sheet, steel_mill)
            if policy_type == "THICKNESS"
            else self.find_width_blocks(sheet, steel_mill)
        )
        policies: List[ParsedPolicy] = []
        for block in blocks:
            policies.extend(
                self._parse_one_block(sheet, steel_mill, policy_type, block)
            )
        return policies

    # ------------------------------------------------------------------ #
    # 子类兼容：委托 assembler / scanner（避免大面积改各钢厂 Handler）
    # ------------------------------------------------------------------ #

    def locate_thickness_block(
        self,
        sheet: Worksheet,
        label_row: int,
        block_end: int,
    ) -> Optional[Dict[str, Any]]:
        return self.assembler.locate_thickness_block(sheet, label_row, block_end)

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
        return self.assembler.locate_width_block(
            sheet,
            title_row,
            block_end,
            grade_col,
            data_col_start,
            max_col,
            category=category,
            header_row_offset=header_row_offset,
            scan_cols=scan_cols,
        )

    def collect_price_cols(
        self,
        sheet: Worksheet,
        header_row: int,
        start_col: int = 2,
        end_col: Optional[int] = None,
    ) -> List[int]:
        return self.scanner.collect_price_cols(sheet, header_row, start_col, end_col)

    def find_block_end_row(
        self,
        sheet: Worksheet,
        start_row: int,
        max_row: int,
        max_col: int,
        *,
        blank_limit: int = BLANK_LIMIT,
        scan_cols: Optional[List[int]] = None,
    ) -> int:
        return self.scanner.find_block_end_row(
            sheet,
            start_row,
            max_row,
            max_col,
            blank_limit=blank_limit,
            scan_cols=scan_cols,
        )

    def find_grade_label_rows(
        self,
        sheet: Worksheet,
        start_row: int = 1,
        end_row: Optional[int] = None,
    ) -> List[int]:
        return self.scanner.find_grade_label_rows(sheet, start_row, end_row)

    def find_section_break_row(
        self,
        sheet: Worksheet,
        start_row: int,
        max_row: int,
        scan_col: int = 1,
    ) -> Optional[int]:
        return self.scanner.find_section_break_row(
            sheet, start_row, max_row, scan_col
        )

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

    def infer_block_category(self, sheet: Worksheet, block: Dict[str, Any]) -> str:
        return self.assembler.infer_block_category(sheet, block)

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

    def _find_value_above_with_row(
        self,
        sheet: Worksheet,
        start_row: int,
        col: int,
        min_row: int = 1,
    ) -> Tuple[int, int]:
        return self.scanner.find_value_above_with_row(
            sheet, start_row, col, min_row
        )
