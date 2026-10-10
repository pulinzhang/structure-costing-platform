"""首钢 Sheet 处理器。"""

from decimal import Decimal
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.handlers.base_handler.base_handler import (
    BaseSheetHandler,
)
from app.parsers.yishiyiyi.policy.handlers.constants import GRADE_LABELS, parse_thickness_label
from app.parsers.yishiyiyi.policy.models.policy_block import PolicyBlock

from ..models.policy import (
    GRADE_TYPE_WIDTH_RANGE,
    POLICY_TYPE_WIDTH,
    ParsedPolicy,
)


class ShougangSheetHandler(BaseSheetHandler):
    """首钢 Sheet 处理器。

    布局（以基准厚度1.0为例）：
        R4:  钢种  厚度加减价,基准厚度1.0——元/吨  ...  冷轧宽度加减价
        R5:        ≥0.5   ≥0.6   ≥0.7  ...           700≤宽＜800  800≤宽＜900  ...  ≥1051
        R6:  DC01   210    180    140  ...                  300       200  ...      0
        R7:  DC03   ...
        ...
        R10:                  镀锌宽度加减价          ← 块标题（合并单元格，end_col=18）
        R11:                  ＜800  800≤宽＜900  900≤宽＜1000  ≥1000
        R12:                  ＞0.5     250       220       170    0
        R13:                  ≤0.5     250       100        50    0

    厚度块：title_col=C2，grade_col=C1（钢种列），header_row=R5，price_cols=C2~C11
    宽度块：grade_col=title_col（C14 合并单元格），price_end_col=18
    """

    # ------------------------------------------------------------------ #
    # 厚度块
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(self, sheet: Worksheet, steel_mill: str) -> list[PolicyBlock]:
        return self.find_default_thickness_blocks(sheet, steel_mill)

    # ------------------------------------------------------------------ #
    # 工具
    # ------------------------------------------------------------------ #

    def _is_width_col_header(self, text: str | None) -> bool:
        """判断列头文本是否为宽度相关（包含"宽"，或为单操作符宽度范围）。"""
        if not text:
            return False
        text = str(text).strip()
        if "宽" in text:
            return True
        # 单操作符宽度：≥1051, ＜800, ≥1000
        if text.startswith("≥") or text.startswith("＞") or text.startswith("<"):
            try:
                num = float(text.lstrip("≥＞<　 "))
                return num >= 100
            except ValueError:
                return True
        return False

    def _find_header_row_in_range(
        self, sheet: Worksheet, title_row: int, scan_end: int
    ) -> int | None:
        """在 title_row+1 到 scan_end 之间，找第一个含宽度列头的行。"""
        for r in range(title_row + 1, scan_end + 1):
            for c in range(1, self.col_max(sheet) + 1):
                if self._is_width_col_header(self.text_or_none(sheet, r, c)):
                    return r
        return None

    def _get_merge_end_col(self, sheet: Worksheet, row: int, col: int) -> Any:
        """返回合并单元格的结束列号；若非合并单元格则返回传入的列号。

        openpyxl 的 max_col 没有类型，标成 int 会触发 no-any-return。
        """
        for merged in sheet.merged_cells.ranges:
            if merged.min_row <= row <= merged.max_row and merged.min_col <= col <= merged.max_col:
                return merged.max_col
        return col

    # ------------------------------------------------------------------ #
    # 块定位
    # ------------------------------------------------------------------ #

    def find_width_blocks(self, sheet: Worksheet, _steel_mill: str) -> list[PolicyBlock]:
        """定位首钢所有宽度块。

        1. 扫描全表，找含"宽度"关键字的行 → 块标题（其合并单元格 end_col 即为价格列终点）
        2. 标题的下一行 → 找第一个含宽度列头的行作为列头行
        3. 从列头行含"宽"的列确定为起始列，标题合并单元格 end_col 为终止列
        4. 在块范围内扫描数据行
        """
        blocks: list[PolicyBlock] = []
        max_row = self.row_max(sheet)
        max_col = self.col_max(sheet)

        w_title_rows: list[int] = []
        w_title_cols: list[int] = []
        for r in range(1, max_row + 1):
            for c in range(1, max_col + 1):
                if self.text_or_none(sheet, r, c) and "宽度" in str(self.text_or_none(sheet, r, c)):
                    w_title_rows.append(r)
                    w_title_cols.append(c)
                    break

        for idx, (title_row, title_col) in enumerate(zip(w_title_rows, w_title_cols, strict=False)):
            scan_end = w_title_rows[idx + 1] - 1 if idx + 1 < len(w_title_rows) else max_row

            header_row = self._find_header_row_in_range(sheet, title_row, scan_end)
            if header_row is None:
                continue

            # 标题合并单元格的 end_col 即为价格列终点
            price_end_col = self._get_merge_end_col(sheet, title_row, title_col)

            # 从列头行含"宽"的列确定为起始列
            width_start_col = None
            for c in range(title_col, max_col + 1):
                if "宽" in str(self.text_or_none(sheet, header_row, c) or ""):
                    width_start_col = c
                    break
            if width_start_col is None:
                continue

            # 收集价格列（title_col+1 到 price_end_col）
            price_cols = [
                c
                for c in range(title_col + 1, price_end_col + 1)
                if self.text_or_none(sheet, header_row, c) is not None
            ]
            if not price_cols:
                continue

            # 扫描数据行
            grade_col = title_col
            data_start = None
            data_end = None
            blank_streak = 0

            for r in range(header_row + 1, scan_end + 1):
                label = self.text_or_none(sheet, r, grade_col)
                has_price = any(self.text_or_none(sheet, r, c) is not None for c in price_cols)
                if label and label not in GRADE_LABELS:
                    if data_start is None:
                        data_start = r
                    blank_streak = 0
                elif not label and has_price:
                    blank_streak = 0
                else:
                    blank_streak += 1
                    if blank_streak >= 1:
                        data_end = r - 1
                        break

            if data_start is None:
                continue
            if data_end is None:
                data_end = scan_end

            title_text = self.text_or_none(sheet, title_row, title_col) or ""
            if "镀锌" in title_text:
                category = "镀锌钢"
            elif "酸洗" in title_text:
                category = "酸洗钢"
            else:
                category = "冷轧钢"

            blocks.append(
                {
                    "category_name": category,
                    "policy_type": "WIDTH",
                    "header_row": header_row,
                    "grade_col": grade_col,
                    "price_cols": sorted(price_cols),
                    "data_row_start": data_start,
                    "data_row_end": data_end,
                    "base_thickness": None,
                    "grade_blacklist": GRADE_LABELS,
                }
            )

        return blocks

    # ------------------------------------------------------------------ #
    # 块解析
    # ------------------------------------------------------------------ #

    def _parse_width_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: PolicyBlock,
    ) -> list[ParsedPolicy]:
        header_row = block["header_row"]
        price_cols = sorted(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block["category_name"]
        grade_col = block["grade_col"]

        boundaries = self._collect_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        policies = []
        for r in range(data_start, data_end + 1):
            thickness_label = self.text_or_none(sheet, r, grade_col)
            if not thickness_label or thickness_label in GRADE_LABELS:
                continue

            raw_items, _ = self._build_items_for_row(
                sheet, r, price_cols, boundaries, POLICY_TYPE_WIDTH, sort_order=r
            )
            if not raw_items:
                continue

            thick_min_raw, thick_min_op, thick_max_raw, thick_max_op = parse_thickness_label(
                thickness_label
            )
            thick_min = Decimal(str(thick_min_raw)) if thick_min_raw is not None else None
            thick_max = Decimal(str(thick_max_raw)) if thick_max_raw is not None else None

            for raw in raw_items:
                raw.target_sub_group = thickness_label
                raw.thick_min = thick_min
                raw.thick_min_operator = thick_min_op or ">="
                raw.thick_max = thick_max
                raw.thick_max_operator = thick_max_op or "<"

            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=category_name,
                    grade_type=GRADE_TYPE_WIDTH_RANGE,
                    grade_value=thickness_label,
                    policy_type=POLICY_TYPE_WIDTH,
                    base_thickness=None,
                    items=raw_items,
                )
            )

        return policies

    # ------------------------------------------------------------------ #
    # 入口
    # ------------------------------------------------------------------ #

    def _parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> list[ParsedPolicy]:
        if policy_type == "WIDTH":
            blocks = self.find_width_blocks(sheet, steel_mill)
            policies = []
            for block in blocks:
                policies.extend(self._parse_width_block(sheet, steel_mill, block))
            return policies
        return self._parse_blocks_default(sheet, steel_mill, policy_type)
