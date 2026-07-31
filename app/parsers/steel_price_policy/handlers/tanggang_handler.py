"""唐钢 Sheet 处理器。

排版特点:
- 顶部：厚度块垂直堆叠（冷轧/镀锌）
- 底部：多个宽度块（A 列起标题，如"冷轧宽度加价"、"镀锌宽度加价"）

宽度加价逻辑（两种行类型）:
1. 钢种行（如 DC01、DC03、"DC04及以上"）：grade_type = GRADE
2. 厚度行（如"厚度≤1.5mm"、"厚度＞1.5mm"）：grade_type = THICKNESS_RANGE

镀锌块每行都是独立政策。
"""
from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from .base_handler import BaseSheetHandler
from .constants import GRADE_LABELS, parse_thickness_label


class TanggangSheetHandler(BaseSheetHandler):
    """唐钢 Sheet 处理器。"""

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        return self.find_default_thickness_blocks(sheet, steel_mill)

    # ------------------------------------------------------------------ #
    # 宽度块：唐钢专用解析
    # ------------------------------------------------------------------ #

    def _parse_tanggang_width_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: Dict[str, Any],
    ) -> List:
        """唐钢宽度块解析：逐行构建政策。

        - 钢种行（DC01、DC03、"DC04及以上"）：grade_type = GRADE
        - 厚度行（"厚度≤1.5mm"、"厚度＞1.5mm"）：grade_type = THICKNESS_RANGE
        """
        from decimal import Decimal

        from ..models import ParsedPolicy
        from ..models.policy import (
            GRADE_TYPE_GRADE,
            GRADE_TYPE_THICKNESS_RANGE,
            POLICY_TYPE_WIDTH,
        )

        header_row = block["header_row"]
        price_cols = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")

        boundaries = self._collect_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        sorted_price_cols = sorted(price_cols)
        policies: List = []

        for r in range(data_start, data_end + 1):
            grade_raw = self.text_or_none(sheet, r, 1)
            if not grade_raw:
                continue

            grade_stripped = grade_raw.strip()
            if grade_stripped in GRADE_LABELS:
                continue

            items, _ = self._build_items_for_row(
                sheet, r, sorted_price_cols, boundaries, POLICY_TYPE_WIDTH, sort_order=r
            )
            if not items:
                continue

            if "厚度" in grade_stripped:
                grade_type = GRADE_TYPE_THICKNESS_RANGE
                thick_min_raw, thick_min_op, thick_max_raw, thick_max_op = parse_thickness_label(
                    grade_stripped
                )
                thick_min = Decimal(str(thick_min_raw)) if thick_min_raw is not None else None
                thick_max = Decimal(str(thick_max_raw)) if thick_max_raw is not None else None
                for item in items:
                    item.thick_min = thick_min
                    item.thick_min_operator = thick_min_op or ">="
                    item.thick_max = thick_max
                    item.thick_max_operator = thick_max_op or "<"
            else:
                grade_type = GRADE_TYPE_GRADE

            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=category_name,
                    grade_type=grade_type,
                    grade_value=grade_stripped,
                    policy_type=POLICY_TYPE_WIDTH,
                    base_thickness=None,
                    items=items,
                )
            )

        return policies

    def _parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List:
        """唐钢定制：WIDTH 政策走专用解析。"""
        if policy_type == "WIDTH":
            blocks = self.find_width_blocks(sheet, steel_mill)
            policies = []
            for block in blocks:
                policies.extend(self._parse_tanggang_width_block(sheet, steel_mill, block))
            return policies
        return self._parse_blocks_default(sheet, steel_mill, policy_type)

    def _parse_blocks_default(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List:
        """THICKNESS 政策的通用解析（复用基类逻辑）。"""
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

    # ------------------------------------------------------------------ #
    # 宽度块定位（复用基类）
    # ------------------------------------------------------------------ #

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        max_row, max_col = self.row_max(sheet), self.col_max(sheet)

        w_title_rows: List[int] = []
        for r in range(1, max_row + 1):
            text = self.text(sheet, r, 1)
            if text and ("宽度加价" in text or "宽度加减价" in text):
                w_title_rows.append(r)

        for i, title_row in enumerate(w_title_rows):
            block_end = w_title_rows[i + 1] - 1 if i + 1 < len(w_title_rows) else max_row
            title_text = self.text(sheet, title_row, 1)
            if "镀锌" in title_text:
                category = "镀锌钢"
            elif "酸洗" in title_text:
                category = "酸洗钢"
            else:
                category = "冷轧钢"

            block = self.locate_width_block(
                sheet, title_row, block_end,
                grade_col=1, data_col_start=2, max_col=max_col,
                category=category,
            )
            if block:
                blocks.append(block)

        return blocks
