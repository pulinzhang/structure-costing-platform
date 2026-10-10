"""唐钢 Sheet 处理器。

排版特点:
- 顶部：厚度块垂直堆叠（冷轧/镀锌）
- 底部：多个宽度块（A 列起标题，如"冷轧宽度加价"、"镀锌宽度加价"）

宽度加价逻辑（两种行类型）:
1. 钢种行（如 DC01、DC03、"DC04及以上"）：grade_type = GRADE
2. 厚度行（如"厚度≤1.5mm"、"厚度＞1.5mm"）：grade_type = THICKNESS_RANGE

镀锌块每行都是独立政策。
"""

from decimal import Decimal
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.boundary_parser import _Boundary
from app.parsers.yishiyiyi.policy.handlers.base_handler.base_handler import (
    BaseSheetHandler,
)

from .constants import GRADE_LABELS, parse_thickness_label


class TanggangSheetHandler(BaseSheetHandler):
    """唐钢 Sheet 处理器。"""

    def find_thickness_blocks(self, sheet: Worksheet, steel_mill: str) -> list[dict[str, Any]]:
        return self.find_default_thickness_blocks(sheet, steel_mill)

    # ------------------------------------------------------------------ #
    # 宽度块：唐钢专用解析
    # ------------------------------------------------------------------ #

    def _parse_tanggang_width_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: dict[str, Any],
    ) -> list[Any]:
        """唐钢宽度块解析：逐行构建政策。

        - 钢种行（DC01、DC03、"DC04及以上"）：grade_type = GRADE
        - 厚度行（"厚度≤1.5mm"、"厚度＞1.5mm"）：grade_type = THICKNESS_RANGE
        """
        from ..models.policy import (
            GRADE_TYPE_GRADE,
            GRADE_TYPE_THICKNESS_RANGE,
            POLICY_TYPE_WIDTH,
            ParsedPolicy,
        )

        header_row = block["header_row"]
        price_cols = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")

        boundaries = self._collect_tanggang_width_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        sorted_price_cols = sorted(price_cols)
        policies: list[Any] = []

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
    ) -> list[Any]:
        """唐钢定制：WIDTH 政策走专用解析。"""
        if policy_type == "WIDTH":
            blocks = self.find_width_blocks(sheet, steel_mill)
            policies = []
            for block in blocks:
                policies.extend(self._parse_tanggang_width_block(sheet, steel_mill, block))
            return policies
        # THICKNESS 政策走基类的通用解析
        return super()._parse_blocks_default(sheet, steel_mill, policy_type)

    # ------------------------------------------------------------------ #
    # 宽度块定位（唐钢专用）
    # ------------------------------------------------------------------ #

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
        """唐钢专用：允许纯数字列头（如 1000mm），不走 _parse_boundary 过滤。"""
        header_row = title_row + header_row_offset
        if header_row > block_end:
            return None

        # 唐钢：手动收集所有非空列头（含纯数字）
        cols = scan_cols if scan_cols is not None else range(data_col_start, max_col + 1)
        price_cols: list[int] = []
        for c in cols:
            raw = sheet.cell(row=header_row, column=c).value
            if raw is not None and str(raw).strip():
                price_cols.append(c)

        if not price_cols:
            return None

        return {
            "category_name": category,
            "policy_type": "WIDTH",
            "grade_col": grade_col,
            "header_row": header_row,
            "price_cols": price_cols,
            "data_row_start": header_row + 1,
            "data_row_end": block_end,
            "base_thickness": None,
            "grade_blacklist": GRADE_LABELS,
        }

    def find_width_blocks(self, sheet: Worksheet, _steel_mill: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        max_row, max_col = self.row_max(sheet), self.col_max(sheet)

        w_title_rows: list[int] = []
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
                sheet,
                title_row,
                block_end,
                grade_col=1,
                data_col_start=2,
                max_col=max_col,
                category=category,
            )
            if block:
                blocks.append(block)

        return blocks

    # ------------------------------------------------------------------ #
    # 唐钢宽度边界收集（处理等号区间）
    # ------------------------------------------------------------------ #
    def _collect_tanggang_width_boundaries(
        self,
        sheet: Worksheet,
        header_row: int,
        price_cols: list[int],
    ) -> dict[int, "_Boundary"]:
        """唐钢宽度边界收集：处理纯数字等号区间。

        唐钢数据中可能出现"1000mm"这样的纯数字，表示精确值区间 1000<=W<=1000。
        需要特殊处理：
        - 纯数字 → min=数字, min_op=">=", max=数字, max_op="<="（等号区间）
        """
        import re

        from app.parsers.yishiyiyi.policy.boundary_parser import _Boundary

        result: dict[int, _Boundary] = {}
        _PURE_NUM_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(?:mm)?\s*$", re.IGNORECASE)

        for c in price_cols:
            raw = sheet.cell(row=header_row, column=c).value
            text = str(raw) if raw is not None else ""

            # 纯数字：表示等号区间 1000 <= W <= 1000
            pure_match = _PURE_NUM_RE.match(text)
            if pure_match:
                num_str = pure_match.group(1)
                num = Decimal(num_str)
                result[c] = _Boundary(
                    min_val=num,
                    min_operator=">=",
                    max_val=num,
                    max_operator="<=",
                )
            else:
                # 非纯数字，使用通用解析
                from app.parsers.yishiyiyi.policy.boundary_parser import _parse_boundary

                b = _parse_boundary(raw)
                if b is not None:
                    result[c] = b

        return result
