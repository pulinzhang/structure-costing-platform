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
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.boundary_parser import _Boundary
from app.parsers.yishiyiyi.policy.handlers.constants import BLANK_LIMIT, GRADE_LABELS
from app.parsers.yishiyiyi.policy.models.ladder_item import ParsedLadderItem
from app.parsers.yishiyiyi.policy.value_parser import _to_int_price
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
        from app.parsers.yishiyiyi.policy.models import ParsedPolicy

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
                        zinc_coating_min=zinc_min,
                        zinc_coating_min_operator=">=",
                        zinc_coating_max=zinc_max,
                        zinc_coating_max_operator="<=",
                        price_adjustment=price,
                        is_base=False,
                        sort_order=0,
                        excel_row=row,
                        excel_col=c,
                    )

                    policies.append(ParsedPolicy(
                        steel_mill=steel_mill,
                        category_name="镀锌钢" + zinc_range + "g/m2",
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
        """解析镀锌量范围字符串，兼容 "-"、"～"、"—" 等分隔符。"""
        from decimal import Decimal
        import re

        if not zinc_range:
            return (None, None)

        # 将各种常见的范围分隔符统一替换为标准的 "-"
        normalized = re.sub(r"[～—―–]", "-", str(zinc_range))
        parts = normalized.split("-")

        if len(parts) == 2:
            try:
                return (Decimal(parts[0].strip()), Decimal(parts[1].strip()))
            except Exception:
                pass
        return (None, None)

    def _get_zinc_price(self, sheet: Worksheet, row: int, col: int) -> int:
        """获取锌层加价价格（四舍五入到元）。"""
        return _to_int_price(sheet.cell(row=row, column=col).value)

    # ------------------------------------------------------------------ #
    # 子类复用的默认厚度块查找
    # ------------------------------------------------------------------ #

    def find_default_thickness_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
    ) -> List[Dict[str, Any]]:
        """默认厚度块扫描: 按三步逻辑找块。

        第一步：找到所有含 "厚度加减价-基准厚度" 或 "厚度加减价" 的单元格
        第二步：从单元格下一行取出加减价范围（boundary 列头）
        第三步：从单元格左边第一列的下一行取出钢种。当钢种单元格为空时，说明这个厚度块结束
        """
        blocks: List[Dict[str, Any]] = []
        max_row = self.scanner.row_max(sheet)
        max_col = self.scanner.col_max(sheet)

        # 第一步：收集所有"厚度加减价"标题单元格的位置
        # 过滤条件：标题的下一行必须是边界行（含 ≥/≤/＞/< 或数字开头）
        title_cells = []
        for r in range(1, max_row + 1):
            for c in range(1, max_col + 1):
                text = self.scanner.text(sheet, r, c)
                if text and ("厚度加减价-基准厚度" in text or "厚度加减价" in text):
                    # 检查下一行是否是边界行
                    next_row_text = self.scanner.text(sheet, r + 1, c)
                    # 边界行特征：包含 ≥/≤/＞/< 或以数字开头
                    if next_row_text and (
                        any(s in next_row_text for s in ["≥", "≤", "＞", "<"])
                        or next_row_text.strip()[0:1].isdigit() if next_row_text.strip() else False
                    ):
                        title_cells.append({"row": r, "col": c, "text": text})

        # 遍历每个标题单元格，提取块信息
        for idx, title_cell in enumerate(title_cells):
            title_row = title_cell["row"]
            title_col = title_cell["col"]

            # 第二步：从标题单元格下一行取出加减价范围（boundary 列头行）
            header_row = title_row + 1

            # 第三步：从标题单元格左边第一列的下一行取出钢种
            # 钢种列 = 标题所在列 - 1（标题通常在数据列之前）
            grade_col = title_col - 1
            for check_c in range(1, title_col + 1):
                cell_text = self.scanner.text(sheet, title_row, check_c)
                if cell_text and any(label in cell_text for label in GRADE_LABELS):
                    grade_col = check_c
                    break

            # 确定块的结束行：从钢种行的下一行开始，当钢种列为空时说明块结束
            block_end = self._find_thickness_block_end(
                sheet, title_row, grade_col, max_row
            )

            if block_end <= header_row:
                continue

            # 收集加减价边界列：从钢种列的下一列开始往右扫，或者从第 2 列开始，避免被大标题的列位置带偏
            start_scan_col = max(2, grade_col + 1)
            price_cols = self._collect_boundary_cols(
                sheet, header_row, start_scan_col
            )
            if not price_cols:
                continue

            # 确定基准厚度
            base_thickness = self.scanner.infer_base_thickness(
                sheet, header_row, title_row
            )

            # 先构建 block（需要 data_row_start 和 data_row_end）
            block = {
                "category_name": "冷轧钢",  # 先用默认值，infer_block_category 会修正
                "policy_type": "THICKNESS",
                "grade_col": grade_col,
                "header_row": header_row,
                "price_cols": price_cols,
                "data_row_start": header_row + 1,
                "data_row_end": block_end,
                "base_thickness": base_thickness,
            }

            # 确定分类
            category_name = self.assembler.infer_block_category(sheet, block)
            block["category_name"] = category_name
            blocks.append(block)

        return blocks

    def _find_thickness_block_end(
        self,
        sheet: Worksheet,
        title_row: int,
        grade_col: int,
        max_row: int,
    ) -> int:
        """从 header_row + 2（即第一个钢种数据行）开始扫描，当钢种列为空时说明这个厚度块结束。"""
        if grade_col < 1:
            grade_col = 1
        start_scan = title_row + 2
        for r in range(start_scan, max_row + 1):
            grade_text = self.scanner.text(sheet, r, grade_col)
            if not grade_text or grade_text.strip() == "":
                return r - 1
        return max_row

    def _collect_boundary_cols(
        self,
        sheet: Worksheet,
        header_row: int,
        title_col: int,
    ) -> List[int]:
        """从 header_row 收集所有含 boundary 的列（加减价范围列）。

        厚度块专用：纯数字规范化为 "<=数字" 后判断，如 0.5 → <=0.5。
        扫描时遇到第一个空 cell 即终止（块的边界由单元格是否为空决定）。
        """
        import re
        from app.parsers.yishiyiyi.policy.boundary_parser import _parse_boundary_thickness

        _PURE_NUM_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")
        scan_end = self.scanner.col_max(sheet)
        cols = []
        for c in range(title_col, scan_end + 1):
            raw = sheet.cell(row=header_row, column=c).value
            if raw is None:
                break
            raw_stripped = str(raw).strip()
            # "最大" 单独出现或 "最大X" 形式 → 无上界，视为有效边界列
            import re as _re
            if _re.match(r"^最大\s*(\d+(?:\.\d+)?)?\s*$", raw_stripped):
                cols.append(c)
                continue
            if isinstance(raw, (int, float)):
                normalized = "<=" + str(raw)
            elif isinstance(raw, str):
                # 处理 "最大2.5" → "<=2.5"
                m = _re.match(r"^最大\s*(\d+(?:\.\d+)?)\s*$", raw_stripped)
                if m:
                    normalized = "<= " + m.group(1)
                elif _PURE_NUM_RE.match(raw_stripped):
                    normalized = "<=" + raw_stripped
                else:
                    normalized = raw_stripped
            else:
                normalized = raw
            if _parse_boundary_thickness(normalized) is not None:
                cols.append(c)
        return cols

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
    ) -> Optional[Dict[str, Any]]:
        """委托给 PolicyAssembler 执行 5 步定位。"""
        return self.assembler.locate_thickness_block(
            sheet, label_row, block_end
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

    def infer_block_category(self, sheet: Worksheet, block: Dict[str, Any]) -> str:
        return self.assembler.infer_block_category(sheet, block)

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

    def _find_value_above_with_row(
        self,
        sheet: Worksheet,
        start_row: int,
        col: int,
        min_row: int = 1,
    ) -> Tuple[int, int]:
        return self.scanner.find_value_above_with_row(sheet, start_row, col, min_row)

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
