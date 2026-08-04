"""VAMA Sheet 处理器。

排版特点:
- 厚度块垂直堆叠（冷轧/镀锌）
- 右侧独立宽度列（Col 10，格式为 "1000-1600"，表示适用宽度范围）
- 每条厚度政策同时关联一个宽度范围，policy_type = THICKNESS_WIDTH

厚度边界逻辑（闭区间示例）：
  ≥0.5   → 0.5 ≤ w < 0.6
  ≥0.6   → 0.6 ≤ w < 0.7
  ≥0.7   → 0.7 ≤ w < 0.8
  ≥0.8   → 0.8 ≤ w < 1.0
  ≥1.0   → 1.0 ≤ w < 1.2
  ≥1.2   → 1.2 ≤ w < 1.5
  ≥1.5   → 1.5 ≤ w < 2.0（注意！到2.0，不是到2.3）
  ≥2.0-2.3 → 2.0 ≤ w ≤ 2.3（显式给定终点，终结档）
"""
import re
from typing import Any, Dict, List, Optional

from openpyxl.worksheet.worksheet import Worksheet

from ..models import ParsedPolicy
from ..models.policy import GRADE_TYPE_GRADE
from ..value_parser import _to_int_price
from app.parsers.steel_price_policy.handlers.base_handler import BaseSheetHandler
from ..boundary_parser import _Boundary
from .constants import GRADE_LABELS

from ..models.ladder_item import ParsedLadderItem
class VamaSheetHandler(BaseSheetHandler):
    """VAMA Sheet 处理器。"""

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        blocks = self.find_default_thickness_blocks(sheet, steel_mill)
        for block in blocks:
            # 读取 Col 10 的宽度范围（如 "1000-1600"）
            width_boundary = self._parse_width_range_from_col10(sheet, block)
            block["width_range"] = width_boundary
            # VAMA 的厚度政策同时带宽度约束，类型改为 THICKNESS_WIDTH
            block["policy_type"] = "THICKNESS_WIDTH"
        return blocks

    def _parse_width_range_from_col10(
        self, sheet: Worksheet, block: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """从 Col 10 读取宽度范围。

        表头行（或数据行）Col 10 通常是 "1000-1600" 这样的格式，
        解析为 {min_val: 1000, min_operator: ">=", max_val: 1600, max_operator: "<="}。
        """
        header_row = block["header_row"]
        data_start = block["data_row_start"]
        max_row = self.row_max(sheet)

        # 先尝试表头行（Row 5 / Row 20）
        raw = self.text(sheet, header_row, 10)
        if raw:
            parsed = self._parse_width_text(raw)
            if parsed:
                return parsed

        # 再尝试数据行第一行
        for r in range(data_start, min(data_start + 5, max_row + 1)):
            raw = self.text(sheet, r, 10)
            if raw:
                parsed = self._parse_width_text(raw)
                if parsed:
                    return parsed

        return None

    def _parse_width_text(self, text: str) -> Optional[Dict[str, Any]]:
        """解析宽度文本，如 "1000-1600" → 闭区间 [1000, 1600]。

        VAMA 的宽度范围均为闭区间（两端都含）。
        """
        text = text.strip()
        if not text:
            return None

        m = re.match(r"^(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)$", text)
        if m:
            lo = float(m.group(1))
            hi = float(m.group(2))
            return {
                "min_val": lo,
                "min_operator": ">=",
                "max_val": hi,
                "max_operator": "<=",
            }

        return None

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        # VAMA 没有独立的宽度政策块
        return []

    def parse(
        self,
        sheet: Worksheet,
        steel_mill: str,
        warnings: List[str],
    ) -> List:
        """VAMA override：调用 VAMA 专用 _parse_one_block，直接注入 width_range。"""
        policies: List = []
        for block in self.find_thickness_blocks(sheet, steel_mill):
            policies.extend(self._parse_one_block(sheet, steel_mill, "THICKNESS", block))
        for block in self.find_width_blocks(sheet, steel_mill):
            policies.extend(self._parse_one_block(sheet, steel_mill, "WIDTH", block))
        return policies

    # ------------------------------------------------------------------ #
    # VAMA 专用：override _parse_one_block，注入 width_range
    # ------------------------------------------------------------------ #

    def _parse_one_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
        block: Dict[str, Any],
    ) -> List[ParsedPolicy]:
        """VAMA override：处理 THICKNESS_WIDTH 类型，在每条 item 上注入 block 的宽度范围。"""
        grade_col = block.get("grade_col")
        header_row = block["header_row"]
        price_cols: List[int] = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")
        base_thickness = block.get("base_thickness")
        grade_blacklist = block.get("grade_blacklist", GRADE_LABELS)
        block_policy_type = block.get("policy_type", policy_type)
        width_range = block.get("width_range")  # VAMA 特有

        boundaries = self._collect_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        sorted_price_cols = sorted(price_cols)

        policies: List[ParsedPolicy] = []
        last_grade: Optional[str] = None
        for r in range(data_start, data_end + 1):
            if grade_col is None:
                continue
            grade = self.text_or_none(sheet, r, grade_col)
            if not grade:
                grade = last_grade
            else:
                last_grade = grade
            if not grade:
                continue
            if grade in grade_blacklist:
                continue
            grade_type = self._infer_grade_type_vama(grade, block_policy_type)
            items = self._build_items_for_row_vama(
                sheet, r, sorted_price_cols, boundaries, width_range, sort_order=r
            )
            if not items:
                continue
            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=category_name,
                    grade_type=grade_type,
                    grade_value=grade,
                    policy_type=block_policy_type,
                    base_thickness=base_thickness,
                    items=items,
                )
            )
        return policies
        header_row = block["header_row"]
        price_cols: List[int] = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")
        base_thickness = block.get("base_thickness")
        grade_blacklist = block.get("grade_blacklist", GRADE_LABELS)
        block_policy_type = block.get("policy_type", policy_type)
        width_range = block.get("width_range")  # VAMA 特有

        boundaries = self._collect_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        sorted_price_cols = sorted(price_cols)

        policies: List[ParsedPolicy] = []
        last_grade: Optional[str] = None
        for r in range(data_start, data_end + 1):
            if grade_col is None:
                continue
            grade = self.text_or_none(sheet, r, grade_col)
            if not grade:
                grade = last_grade
            else:
                last_grade = grade
            if not grade:
                continue
            if grade in grade_blacklist:
                continue
            grade_type = self._infer_grade_type_vama(grade, block_policy_type)
            items = self._build_items_for_row_vama(
                sheet, r, sorted_price_cols, boundaries, width_range, sort_order=r
            )
            if not items:
                continue
            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=category_name,
                    grade_type=grade_type,
                    grade_value=grade,
                    policy_type=block_policy_type,
                    base_thickness=base_thickness,
                    items=items,
                )
            )
        return policies

    def _build_items_for_row_vama(
        self,
        sheet: Worksheet,
        r: int,
        price_cols: List[int],
        boundaries: Dict[int, _Boundary],
        width_range: Optional[Dict[str, Any]],
        sort_order: int = 0,
    ) -> List[ParsedLadderItem]:
        """VAMA 专用：构建行内阶梯项，同时注入宽度范围（双维度 THICKNESS_WIDTH）。"""
        items: List[ParsedLadderItem] = []
        sorted_cols = sorted(price_cols)

        for i, c in enumerate(sorted_cols):
            if c not in boundaries:
                continue
            price_cell = sheet.cell(row=r, column=c)
            if price_cell.value is None:
                start_row = self.find_start_row(sheet, r, c)
                if start_row is not None:
                    start_val = sheet.cell(row=start_row, column=c).value
                    if start_val is not None:
                        price = _to_int_price(start_val)
                    else:
                        price = self._find_value_above(sheet, start_row, c)
                else:
                    price = 0
            else:
                price = _to_int_price(price_cell.value)

            boundary = boundaries[c]

            # 推断上界
            if boundary.max_val is None and i < len(sorted_cols) - 1:
                next_c = sorted_cols[i + 1]
                if next_c in boundaries:
                    next_boundary = boundaries[next_c]
                    if next_boundary.min_val is not None:
                        boundary = _Boundary(
                            min_val=boundary.min_val,
                            min_operator=boundary.min_operator,
                            max_val=next_boundary.min_val,
                            max_operator="<",
                        )

            if width_range is not None:
                w_min = width_range.get("min_val")
                w_min_op = width_range.get("min_operator", ">=")
                w_max = width_range.get("max_val")
                w_max_op = width_range.get("max_operator", "<=")
            else:
                w_min = None
                w_min_op = ">="
                w_max = None
                w_max_op = "<"

            items.append(
                ParsedLadderItem(
                    target_sub_group=None,
                    thick_min=boundary.min_val,
                    thick_min_operator=boundary.min_operator,
                    thick_max=boundary.max_val,
                    thick_max_operator=boundary.max_operator,
                    width_min=w_min,
                    width_min_operator=w_min_op,
                    width_max=w_max,
                    width_max_operator=w_max_op,
                    price_adjustment=price,
                    is_base=False,
                    sort_order=sort_order,
                )
            )
        return items

    # ------------------------------------------------------------------ #
    # VAMA 专用：grade_type 推断（THICKNESS_WIDTH 政策下 grade 始终是钢种）
    # ------------------------------------------------------------------ #

    def _infer_grade_type_vama(self, grade: str, policy_type: str) -> str:
        """VAMA THICKNESS_WIDTH 政策：grade 必定是钢种牌号，始终返回 GRADE。"""
        return GRADE_TYPE_GRADE
