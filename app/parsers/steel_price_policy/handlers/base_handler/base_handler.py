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
        """解析入口：厚度块 + 宽度块 + 锌层加价块。"""
        policies: List = []
        policies.extend(self._parse_blocks(sheet, steel_mill, "THICKNESS"))
        policies.extend(self._parse_blocks(sheet, steel_mill, "WIDTH"))
        policies.extend(self.parse_zinc_coating_blocks(sheet, steel_mill))
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
    # 锌层加价块查找（通用）
    # ------------------------------------------------------------------ #

    def find_zinc_coating_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """查找所有"锌层加价"表块。

        表结构（严格以"锌层加价"为识别因子）：
            R33: 镀锌量g/m2 | 80-90 | 91-120 | 121-140 | 141-160 | 161-180 | 181-200
            R34: 厚度≥0.6mm加价(元/吨) | 0 | 46 | 91 | 135 | 180 | 226
            R35: 厚度<0.6mm加价(元/吨) | 0 | 46 | 91 | 135 | 180 | 270

        镀锌量范围格式固定为 "数字-数字" 闭区间。
        """
        import re
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = self.col_max(sheet)

        zinc_label_rows: List[int] = []
        for r in range(1, max_row + 1):
            text = self.text(sheet, r, 1)
            if text and "锌层加价" in text:
                zinc_label_rows.append(r)

        zinc_pattern = re.compile(r"^\d+\s*-\s*\d+$")

        for label_row in zinc_label_rows:
            range_row = label_row + 1
            thick_ge_row = label_row + 2
            thick_lt_row = label_row + 3

            # 验证镀锌量范围行
            range_text = self.text(sheet, range_row, 1)
            if not range_text or "镀锌量" not in range_text:
                continue

            # 收集镀锌量范围列
            zinc_cols: List[int] = []
            zinc_ranges: List[str] = []
            for c in range(2, max_col + 1):
                val = sheet.cell(row=range_row, column=c).value
                if val and zinc_pattern.match(str(val).strip()):
                    zinc_cols.append(c)
                    zinc_ranges.append(str(val).strip())

            if not zinc_cols:
                continue

            # 验证价格行
            thick_ge_ok = self.text(sheet, thick_ge_row, 1) and bool(
                re.search(r"厚度≥0\.6mm加价", self.text(sheet, thick_ge_row, 1) or "")
            )
            thick_lt_ok = self.text(sheet, thick_lt_row, 1) and bool(
                re.search(r"厚度<0\.6mm加价", self.text(sheet, thick_lt_row, 1) or "")
            )
            if not (thick_ge_ok and thick_lt_ok):
                continue

            blocks.append({
                "policy_type": "ZINC_COATING",
                "label_row": label_row,
                "range_row": range_row,
                "thick_ge_row": thick_ge_row,
                "thick_lt_row": thick_lt_row,
                "zinc_cols": zinc_cols,
                "zinc_ranges": zinc_ranges,
            })

        return blocks

    # ------------------------------------------------------------------ #
    # 锌层加价块解析
    # ------------------------------------------------------------------ #

    def parse_zinc_coating_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List:
        """解析所有锌层加价块，返回 ParsedPolicy 列表。"""
        from decimal import Decimal
        from app.parsers.steel_price_policy.models import ParsedPolicy

        blocks = self.find_zinc_coating_blocks(sheet, steel_mill)
        policies: List = []

        for block in blocks:
            zinc_cols = block["zinc_cols"]
            zinc_ranges = block["zinc_ranges"]
            thick_ge_row = block["thick_ge_row"]
            thick_lt_row = block["thick_lt_row"]

            thickness_conditions = [
                (thick_ge_row, "≥0.6mm"),
                (thick_lt_row, "<0.6mm"),
            ]

            for row, thick_cond in thickness_conditions:
                thick_min_raw, thick_min_op, thick_max_raw, thick_max_op = self._parse_zinc_thickness_cond(thick_cond)
                thick_min = Decimal(str(thick_min_raw)) if thick_min_raw else None
                thick_max = Decimal(str(thick_max_raw)) if thick_max_raw else None

                for c, zinc_range in zip(zinc_cols, zinc_ranges):
                    price = self._get_zinc_price(sheet, row, c)
                    zinc_min, zinc_max = self._parse_zinc_range(zinc_range)

                    item = ParsedLadderItem(
                        target_sub_group=None,
                        thick_min=thick_min,
                        thick_min_operator=thick_min_op or ">=",
                        thick_max=thick_max,
                        thick_max_operator=thick_max_op or "<",
                        width_min=zinc_min,
                        width_min_operator=">=",
                        width_max=zinc_max,
                        width_max_operator="<=",
                        price_adjustment=price,
                        is_base=False,
                        sort_order=0,
                    )

                    policies.append(ParsedPolicy(
                        steel_mill=steel_mill,
                        category_name="镀锌钢",
                        grade_type="THICKNESS_COND",
                        grade_value=thick_cond,
                        policy_type="ZINC_COATING",
                        base_thickness=None,
                        items=[item],
                    ))

        return policies

    def _parse_zinc_thickness_cond(self, cond: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """解析厚度条件字符串，如 "≥0.6mm" 或 "<0.6mm"。"""
        if cond.startswith("≥"):
            val = cond[1:].rstrip("mm").strip()
            return (val, ">=", None, None)
        elif cond.startswith("<"):
            val = cond[1:].rstrip("mm").strip()
            return (None, None, val, "<")
        return (None, None, None, None)

    def _parse_zinc_range(self, zinc_range: str) -> Tuple[Optional["Decimal"], Optional["Decimal"]]:
        """解析镀锌量范围字符串，如 "80-90"（闭区间）。"""
        from decimal import Decimal
        parts = zinc_range.split("-")
        if len(parts) == 2:
            try:
                return (Decimal(parts[0].strip()), Decimal(parts[1].strip()))
            except Exception:
                pass
        return (None, None)

    def _get_zinc_price(self, sheet: Worksheet, row: int, col: int) -> int:
        """获取锌层加价价格。"""
        cell_val = sheet.cell(row=row, column=col).value
        if cell_val is None:
            return 0
        try:
            return int(float(cell_val))
        except Exception:
            return 0

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

            title_row = self.scanner.find_thickness_title_row(
                sheet, label_row, block_end, scan_cols=list(range(2, max_col + 1))
            )
            if title_row is None:
                last_end = label_row + 1
                continue

            thickness_end_col = self.scanner.find_thickness_end_col(
                sheet, title_row, max_col
            )

            block = self.assembler.locate_thickness_block(
                sheet, label_row, block_end, thickness_end_col
            )
            if block:
                block["category_name"] = self.assembler.infer_block_category(
                    sheet, block, max_col=thickness_end_col
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
        """向下扫描块末尾, 提前停在出现宽度标题或锌层加价标题的行."""
        blank_streak = 0
        for r in range(start_row, max_row + 1):
            text = self.scanner.text(sheet, r, 1)
            if text and ("宽度加减价" in text or "宽度加价" in text or "锌层加价" in text):
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
