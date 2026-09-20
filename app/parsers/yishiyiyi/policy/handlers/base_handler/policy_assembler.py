"""PolicyAssembler：封装所有"业务语义解析"逻辑。

职责拆到同目录独立类，本文件只装配并委托：
- 块定位 / 边界推断 → locate_blocks.py
- 阶梯项构建 → build_items.py
- 政策构建 → build_policies.py
- category 推断 → category_inference.py

对外仍从此文件导入 PolicyAssembler。
"""

from __future__ import annotations

from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.boundary_parser import _Boundary
from app.parsers.yishiyiyi.policy.models.ladder_item import ParsedLadderItem
from app.parsers.yishiyiyi.policy.models.policy import ParsedPolicy

from .build_items import ItemBuilder
from .build_policies import PolicyBuilder
from .category_inference import CategoryInference
from .locate_blocks import BlockLocator
from .sheet_scanner import SheetScanner


class PolicyAssembler:
    """政策装配器：封装业务语义解析逻辑。"""

    def __init__(self, scanner: SheetScanner | None = None) -> None:
        self.scanner = scanner or SheetScanner()
        self._locator = BlockLocator(self.scanner)
        self._items = ItemBuilder(self.scanner, self._locator)
        self._policies = PolicyBuilder(self.scanner, self._locator, self._items)
        self._categories = CategoryInference()

    def locate_thickness_block(
        self,
        sheet: Worksheet,
        label_row: int,
        block_end: int,
    ) -> dict[str, Any] | None:
        return self._locator.locate_thickness_block(sheet, label_row, block_end)

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
    ) -> dict[str, Any] | None:
        return self._locator.locate_width_block(
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

    def collect_boundaries(
        self,
        sheet: Worksheet,
        header_row: int,
        price_cols: list[int],
    ) -> dict[int, _Boundary]:
        return self._locator.collect_boundaries(sheet, header_row, price_cols)

    def collect_boundaries_thickness(
        self,
        sheet: Worksheet,
        header_row: int,
        price_cols: list[int],
    ) -> dict[int, _Boundary]:
        return self._locator.collect_boundaries_thickness(sheet, header_row, price_cols)

    def infer_upper_bound(
        self,
        boundary: _Boundary,
        sorted_cols: list[int],
        col_idx: int,
        boundaries: dict[int, _Boundary],
        policy_type: str = "WIDTH",
    ) -> _Boundary:
        return self._locator.infer_upper_bound(
            boundary, sorted_cols, col_idx, boundaries, policy_type
        )

    def infer_grade_type(self, grade: str, policy_type: str) -> str:
        return self._items.infer_grade_type(grade, policy_type)

    def build_items_for_row(
        self,
        sheet: Worksheet,
        r: int,
        price_cols: list[int],
        boundaries: dict[int, _Boundary],
        policy_type: str = "THICKNESS",
        sort_order: int = 0,
    ) -> tuple[list[ParsedLadderItem], Any]:
        return self._items.build_items_for_row(
            sheet, r, price_cols, boundaries, policy_type, sort_order
        )

    def build_item(
        self,
        boundary: _Boundary,
        price: int,
        width_boundary: _Boundary | None = None,
        excel_row: int = 0,
        excel_col: int = 0,
    ) -> ParsedLadderItem:
        return self._items.build_item(boundary, price, width_boundary, excel_row, excel_col)

    def build_policies_from_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: dict[str, Any],
    ) -> list[ParsedPolicy]:
        return self._policies.build_policies_from_block(sheet, steel_mill, block)

    def category_from_grade_name(self, grade: str) -> str:
        return self._categories.category_from_grade_name(grade)

    def infer_block_category(
        self,
        sheet: Worksheet,
        block: dict[str, Any],
    ) -> str:
        return self._categories.infer_block_category(sheet, block)
