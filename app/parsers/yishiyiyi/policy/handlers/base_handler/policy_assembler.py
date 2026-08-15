"""PolicyAssembler：封装所有"业务语义解析"逻辑。

职责：
- 块定位（locate_thickness_block / locate_width_block）
- 边界推断（collect_boundaries / infer_upper_bound）
- grade_type 推断（infer_grade_type）
- 阶梯项构建（build_items_for_row / build_item）
- 政策构建（build_policies_from_block）
- category 推断（category_from_grade_name / infer_block_category）

所有方法均依赖 SheetScanner 完成底层读取，自己只负责"语义"层面。
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.boundary_parser import (
    _Boundary,
    _parse_boundary,
    is_lte,
    is_strict_gt,
)
from app.parsers.yishiyiyi.policy.models import ParsedLadderItem, ParsedPolicy
from app.parsers.yishiyiyi.policy.models.policy import (
    GRADE_TYPE_CATEGORY,
    GRADE_TYPE_GRADE,
    GRADE_TYPE_WIDTH_RANGE,
    POLICY_TYPE_THICKNESS,
)
from app.parsers.yishiyiyi.policy.value_parser import _to_int_price
from app.parsers.yishiyiyi.policy.handlers.constants import GRADE_LABELS
from .sheet_scanner import SheetScanner

_WIDTH_RANGE_KEYWORDS = ("≤", "≥", "＜", "＞", "W", "宽")
_CATEGORY_NAMES = frozenset({"冷轧钢", "镀锌钢", "酸洗钢", "热轧钢"})


class PolicyAssembler:
    """政策装配器：封装业务语义解析逻辑。"""

    def __init__(self, scanner: Optional[SheetScanner] = None):
        self.scanner = scanner or SheetScanner()

    # ------------------------------------------------------------------ #
    # 块定位（5步 / 3步定位协议）
    # ------------------------------------------------------------------ #

    def locate_thickness_block(
        self,
        sheet: Worksheet,
        label_row: int,
        block_end: int,
    ) -> Optional[Dict[str, Any]]:
        """执行厚度块的 5 步定位，返回块描述或 None。"""
        title_row = self.scanner.find_thickness_title_row(
            sheet, label_row, block_end, scan_cols=None
        )
        if title_row is None:
            return None

        header_row = self.scanner.find_header_row(
            sheet, title_row + 1, block_end, scan_cols=None
        )
        if header_row is None:
            return None

        # header 行遇到第一个空 cell 即终止扫描
        price_cols = self.scanner.collect_price_cols_thickness(
            sheet, header_row, start_col=2
        )
        if not price_cols:
            return None

        data_end = block_end
        base_thickness = self.scanner.infer_base_thickness(
            sheet, header_row, label_row
        )
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
        scan_cols: Optional[List[int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """执行宽度块的 3 步定位，返回块描述。"""
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

    # ------------------------------------------------------------------ #
    # 边界收集与推断
    # ------------------------------------------------------------------ #

    def collect_boundaries(
        self,
        sheet: Worksheet,
        header_row: int,
        price_cols: List[int],
    ) -> Dict[int, _Boundary]:
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
        price_cols: List[int],
    ) -> Dict[int, _Boundary]:
        """从列头行收集所有边界定义（厚度专用）。

        纯数字（如 "0.5"）规范化为 "<=0.5" 后解析，解析为 min=None, max=数字, max_operator="<="。
        """
        import re
        from app.parsers.yishiyiyi.policy.boundary_parser import _parse_boundary_thickness

        _PURE_NUM_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")
        result = {}
        for c in price_cols:
            raw = sheet.cell(row=header_row, column=c).value
            # 纯数字开头：原始数据不规范，补全为 "<=数字" 使其规范
            if isinstance(raw, (int, float)):
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
        sorted_cols: List[int],
        col_idx: int,
        boundaries: Dict[int, _Boundary],
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
        if max_val is None:
            if col_idx < len(sorted_cols) - 1:
                # 有下一列，从下一列的 min_val / min_operator 推断
                # 例：≥1.0 | ＞2.0 → 当前 1.0≤t≤2.0（下一档严格大于，本档闭上界）
                # 例：≥0.9 | ≥1.0 → 当前 0.9≤t<1.0（下一档含等号，本档开上界）
                # 全角/半角（＞/>、≥/>=）均通过 is_strict_gt 识别
                next_c = sorted_cols[col_idx + 1]
                if next_c in boundaries:
                    next_boundary = boundaries[next_c]
                    if next_boundary.min_val is not None:
                        max_val = next_boundary.min_val
                        if is_strict_gt(next_boundary.min_operator):
                            max_op = "<="
                        else:
                            max_op = "<"
            # else: 最后一列且无上界，max_val 保持 None（表示 ∞）

        return _Boundary(
            min_val=min_val,
            min_operator=min_op,
            max_val=max_val,
            max_operator=max_op,
        )

    # ------------------------------------------------------------------ #
    # grade_type 推断
    # ------------------------------------------------------------------ #

    def infer_grade_type(self, grade: str, policy_type: str) -> str:
        """推断 grade 的语义类型。"""
        if policy_type == "THICKNESS":
            return GRADE_TYPE_GRADE
        grade_stripped = grade.strip()
        if any(kw in grade_stripped for kw in _WIDTH_RANGE_KEYWORDS):
            return GRADE_TYPE_WIDTH_RANGE
        if grade_stripped in _CATEGORY_NAMES:
            return GRADE_TYPE_CATEGORY
        return GRADE_TYPE_GRADE

    # ------------------------------------------------------------------ #
    # 阶梯项构建
    # ------------------------------------------------------------------ #

    def build_items_for_row(
        self,
        sheet: Worksheet,
        r: int,
        price_cols: List[int],
        boundaries: Dict[int, _Boundary],
        policy_type: str = "THICKNESS",
        sort_order: int = 0,
    ) -> Tuple[List[ParsedLadderItem], Any]:
        """构建行内阶梯明细项列表。返回 (items, extra)。"""
        items: List[ParsedLadderItem] = []
        sorted_cols = sorted(price_cols)
        for i, c in enumerate(sorted_cols):
            if c not in boundaries:
                continue

            price_cell = sheet.cell(row=r, column=c)
            if price_cell.value is None:
                start_row = self.scanner.find_start_row(sheet, r, c)
                if start_row is not None:
                    start_val = sheet.cell(row=start_row, column=c).value
                    if start_val is not None:
                        price = _to_int_price(start_val)
                        price_row = start_row
                    else:
                        price, price_row = self.scanner.find_value_above_with_row(
                            sheet, start_row, c
                        )
                else:
                    price = 0
                    price_row = r
            else:
                price = _to_int_price(price_cell.value)
                price_row = r

            boundary = self.infer_upper_bound(
                boundaries[c], sorted_cols, i, boundaries, policy_type
            )

            if policy_type == "THICKNESS":
                items.append(self._make_thickness_item(boundary, price, sort_order, price_row, c))
            else:
                items.append(self._make_width_item(boundary, price, sort_order, price_row, c))

        return items, None

    @staticmethod
    def _make_thickness_item(
        boundary: _Boundary, price: int, sort_order: int, excel_row: int, excel_col: int
    ) -> ParsedLadderItem:
        return ParsedLadderItem(
            target_sub_group=None,
            thick_min=boundary.min_val,
            thick_min_operator=boundary.min_operator,
            thick_max=boundary.max_val,
            thick_max_operator=boundary.max_operator,
            width_min=None,
            width_min_operator=">=",
            width_max=None,
            width_max_operator="<",
            price_adjustment=price,
            is_base=False,
            sort_order=sort_order,
            excel_row=excel_row,
            excel_col=excel_col,
        )

    @staticmethod
    def _make_width_item(
        boundary: _Boundary, price: int, sort_order: int, excel_row: int, excel_col: int
    ) -> ParsedLadderItem:
        return ParsedLadderItem(
            target_sub_group=None,
            thick_min=None,
            thick_min_operator=">=",
            thick_max=None,
            thick_max_operator="<",
            width_min=boundary.min_val,
            width_min_operator=boundary.min_operator,
            width_max=boundary.max_val,
            width_max_operator=boundary.max_operator,
            price_adjustment=price,
            is_base=False,
            sort_order=sort_order,
            excel_row=excel_row,
            excel_col=excel_col,
        )

    def build_item(
        self,
        boundary: _Boundary,
        price: int,
        width_boundary: Optional[_Boundary] = None,
        excel_row: int = 0,
        excel_col: int = 0,
    ) -> ParsedLadderItem:
        """构建阶梯明细项（单维度或双维度）。"""
        if width_boundary is not None:
            return ParsedLadderItem(
                target_sub_group=None,
                thick_min=boundary.min_val,
                thick_min_operator=boundary.min_operator,
                thick_max=boundary.max_val,
                thick_max_operator=boundary.max_operator,
                width_min=width_boundary.min_val,
                width_min_operator=width_boundary.min_operator,
                width_max=width_boundary.max_val,
                width_max_operator=width_boundary.max_operator,
                price_adjustment=price,
                is_base=False,
                sort_order=0,
                excel_row=excel_row,
                excel_col=excel_col,
            )
        else:
            return ParsedLadderItem(
                target_sub_group=None,
                thick_min=boundary.min_val,
                thick_min_operator=boundary.min_operator,
                thick_max=boundary.max_val,
                thick_max_operator=boundary.max_operator,
                width_min=None,
                width_min_operator=">=",
                width_max=None,
                width_max_operator="<",
                price_adjustment=price,
                is_base=False,
                sort_order=0,
                excel_row=excel_row,
                excel_col=excel_col,
            )

    # ------------------------------------------------------------------ #
    # 政策构建（单块 → ParsedPolicy 列表）
    # ------------------------------------------------------------------ #

    def build_policies_from_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: Dict[str, Any],
    ) -> List[ParsedPolicy]:
        """给定块描述，构建 ParsedPolicy 列表。"""
        grade_col = block.get("grade_col")
        header_row = block["header_row"]
        price_cols = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")
        base_thickness = block.get("base_thickness")
        grade_blacklist = block.get("grade_blacklist", GRADE_LABELS)
        policy_type = block.get("policy_type", POLICY_TYPE_THICKNESS)

        if policy_type == POLICY_TYPE_THICKNESS:
            boundaries = self.collect_boundaries_thickness(sheet, header_row, price_cols)
        else:
            boundaries = self.collect_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        sorted_price_cols = sorted(price_cols)
        policies: List[ParsedPolicy] = []

        for r in range(data_start, data_end + 1):
            if grade_col is None:
                continue
            grade = self.scanner.text_or_none(sheet, r, grade_col)
            if not grade:
                continue
            # 钢种列 "B250P1//HC260Y" 可能是操作人员笔误，将 "//" 替换为 "/"
            if "//" in grade:
                grade = grade.replace("//", "/")
            if grade in grade_blacklist:
                continue

            grade_type = self.infer_grade_type(grade, policy_type)
            items, _ = self.build_items_for_row(
                sheet, r, sorted_price_cols, boundaries, policy_type, sort_order=r
            )
            if not items:
                continue

            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=category_name,
                    grade_type=grade_type,
                    grade_value=grade,
                    policy_type=policy_type,
                    base_thickness=base_thickness,
                    items=items,
                )
            )
        return policies

    # ------------------------------------------------------------------ #
    # category 推断
    # ------------------------------------------------------------------ #

    _GALVANIZED_SUFFIXES: tuple[str, ...] = ("+Z", "+ZF", "+ZM", "+ZA", "+AZ")
    _PICKLED_SUFFIXES: tuple[str, ...] = ("+A",)
    _PICKLED_GRADES: frozenset[str] = frozenset({
        "SPHC", "SPHD", "SPHE", "SPHF",
        "SAPH370", "SAPH400", "SAPH440",
        "QStE340TM", "QStE380TM", "QStE420TM", "QStE460TM", "QStE500TM",
        "QSTE420TM", "QSTE460TM", "QSTE500TM",
        "B510L", "B590L",
    })

    def category_from_grade_name(self, grade: str) -> str:
        """按钢种名后缀/名称推断 category。"""
        if not grade:
            return "冷轧钢"
        for suf in self._GALVANIZED_SUFFIXES:
            if grade.endswith(suf):
                return "镀锌钢"
        if grade in self._PICKLED_GRADES:
            return "酸洗钢"
        for suf in self._PICKLED_SUFFIXES:
            if grade.endswith(suf):
                return "酸洗钢"
        return "冷轧钢"

    def infer_block_category(
        self,
        sheet: Worksheet,
        block: Dict[str, Any],
    ) -> str:
        """综合'字面 hint'与'grade 后缀'推断块的 category。"""
        literal_cat = block.get("category_name") or "冷轧钢"
        if literal_cat != "冷轧钢":
            return literal_cat

        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        grade_col = block.get("grade_col", 1)
        galvanized = pickled = cold = 0
        for r in range(data_start, data_end + 1):
            v = sheet.cell(row=r, column=grade_col).value
            if v is None:
                continue
            t = str(v).strip()
            # 钢种列 "B250P1//HC260Y" 可能是操作人员笔误，将 "//" 替换为 "/"
            if "//" in t:
                t = t.replace("//", "/")
            if not t or t in GRADE_LABELS:
                continue
            cat = self.category_from_grade_name(t)
            if cat == "镀锌钢":
                galvanized += 1
            elif cat == "酸洗钢":
                pickled += 1
            else:
                cold += 1

        if galvanized and not cold:
            return "镀锌钢"
        if pickled and not cold:
            return "酸洗钢"
        if galvanized and cold:
            if galvanized > cold:
                return "镀锌钢"
            if pickled > cold:
                return "酸洗钢"
            return "冷轧钢"
        if pickled and cold:
            return "酸洗钢" if pickled > cold else "冷轧钢"
        return "冷轧钢"