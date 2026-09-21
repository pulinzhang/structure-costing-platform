"""锌层加价块查找与解析。

从 BaseSheetHandler 拆出，避免基类堆积专用表解析逻辑。
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.models.ladder_item import ParsedLadderItem
from app.parsers.yishiyiyi.policy.models.policy import ParsedPolicy
from app.parsers.yishiyiyi.policy.value_parser import _to_int_price

from .sheet_scanner import SheetScanner

_ZINC_RANGE_PATTERN = re.compile(r"^\d+\s*-\s*\d+$")


class ZincCoatingParser:
    """锌层加价表块：定位 + 解析为 ParsedPolicy。"""

    def __init__(self, scanner: SheetScanner | None = None):
        self.scanner = scanner or SheetScanner()

    def find_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
    ) -> list[dict[str, Any]]:
        """查找所有「锌层加价」表块。

        表结构（严格以「锌层加价」为识别因子）：
            R33: 镀锌量g/m2 | 80-90 | 91-120 | ...
            R34: 厚度≥0.6mm加价(元/吨) | ...
            R35: 厚度<0.6mm加价(元/吨) | ...

        镀锌量范围格式固定为「数字-数字」闭区间。
        """
        del steel_mill  # 查找不依赖钢厂；签名与调用方对齐
        blocks: list[dict[str, Any]] = []
        max_row = self.scanner.row_max(sheet)
        max_col = self.scanner.col_max(sheet)

        zinc_label_rows: list[int] = []
        for row in range(1, max_row + 1):
            text = self.scanner.text(sheet, row, 1)
            if text and "锌层加价" in text:
                zinc_label_rows.append(row)

        for label_row in zinc_label_rows:
            range_row = label_row + 1
            thick_ge_row = label_row + 2
            thick_lt_row = label_row + 3

            range_text = self.scanner.text(sheet, range_row, 1)
            if not range_text or "镀锌量" not in range_text:
                continue

            zinc_cols: list[int] = []
            zinc_ranges: list[str] = []
            for col in range(2, max_col + 1):
                value = sheet.cell(row=range_row, column=col).value
                if value and _ZINC_RANGE_PATTERN.match(str(value).strip()):
                    zinc_cols.append(col)
                    zinc_ranges.append(str(value).strip())

            if not zinc_cols:
                continue

            thick_ge_text = self.scanner.text(sheet, thick_ge_row, 1)
            thick_lt_text = self.scanner.text(sheet, thick_lt_row, 1)
            thick_ge_ok = thick_ge_text and bool(re.search(r"厚度≥0\.6mm加价", thick_ge_text))
            thick_lt_ok = thick_lt_text and bool(re.search(r"厚度<0\.6mm加价", thick_lt_text))
            if not (thick_ge_ok and thick_lt_ok):
                continue

            blocks.append(
                {
                    "policy_type": "ZINC_COATING",
                    "label_row": label_row,
                    "range_row": range_row,
                    "thick_ge_row": thick_ge_row,
                    "thick_lt_row": thick_lt_row,
                    "zinc_cols": zinc_cols,
                    "zinc_ranges": zinc_ranges,
                }
            )

        return blocks

    def parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
    ) -> list[ParsedPolicy]:
        """解析所有锌层加价块，返回 ParsedPolicy 列表。"""
        blocks = self.find_blocks(sheet, steel_mill)
        policies: list[ParsedPolicy] = []

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
                (
                    thick_min_raw,
                    thick_min_op,
                    thick_max_raw,
                    thick_max_op,
                ) = self._parse_thickness_cond(thick_cond)
                thick_min = Decimal(str(thick_min_raw)) if thick_min_raw else None
                thick_max = Decimal(str(thick_max_raw)) if thick_max_raw else None

                for col, zinc_range in zip(zinc_cols, zinc_ranges, strict=False):
                    price = _to_int_price(sheet.cell(row=row, column=col).value)
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
                        excel_col=col,
                    )

                    policies.append(
                        ParsedPolicy(
                            steel_mill=steel_mill,
                            category_name="镀锌钢" + zinc_range + "g/m2",
                            grade_type="THICKNESS_COND",
                            grade_value=thick_cond,
                            policy_type="ZINC_COATING",
                            base_thickness=None,
                            items=[item],
                        )
                    )

        return policies

    @staticmethod
    def _parse_thickness_cond(
        cond: str,
    ) -> tuple[str | None, str | None, str | None, str | None]:
        """解析厚度条件字符串，如「≥0.6mm」或「<0.6mm」。"""
        if cond.startswith("≥"):
            value = cond[1:].removesuffix("mm").strip()
            return (value, ">=", None, None)
        if cond.startswith("<"):
            value = cond[1:].removesuffix("mm").strip()
            return (None, None, value, "<")
        return (None, None, None, None)

    @staticmethod
    def _parse_zinc_range(
        zinc_range: str,
    ) -> tuple[Decimal | None, Decimal | None]:
        """解析镀锌量范围字符串，兼容「-」「～」「—」等分隔符。"""
        if not zinc_range:
            return (None, None)

        normalized = re.sub(r"[～—―–]", "-", str(zinc_range))
        parts = normalized.split("-")

        if len(parts) == 2:
            try:
                return (Decimal(parts[0].strip()), Decimal(parts[1].strip()))
            except Exception:
                pass
        return (None, None)
