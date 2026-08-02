"""首钢 Sheet 处理器。"""

from decimal import Decimal
from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.steel_price_policy.handlers.base_handler import BaseSheetHandler
from app.parsers.steel_price_policy.handlers.constants import GRADE_LABELS, parse_thickness_label
from app.parsers.steel_price_policy.boundary_parser import _parse_boundary
from ..models import ParsedPolicy
from ..models.policy import GRADE_TYPE_WIDTH_RANGE, POLICY_TYPE_WIDTH

# 宽度 boundary 特有的正则（用于区分厚度单边标签 vs 真正的宽度范围）
import re

_WIDTH_BOUNDARY_PATTERN = re.compile(
    r"^.*?"          # 可能有前缀数字
    r"(?:<|＜|<=|≤|＜=)"  # 左操作符
    r".*?"           # 可能有变量名
    r"(?:<|＜|<=|≤|＜=)"  # 右操作符
    r".*?$"          # 任意后缀
)


class ShougangSheetHandler(BaseSheetHandler):
    """首钢 Sheet 处理器。

    布局：
        R4:  钢种 厚度加减价,基准厚度1.0——元/吨  ...  冷轧宽度加减价
        R5:       ≤0.5  ≤0.6  ≤0.7  ...            <1500  <1600  ...
        R6: DC01   210   180   140  ...              180    300   ...
        R8:  冷轧宽度加减价          ← 块标题
        R9:   700≤宽＜800  800≤宽＜900  900≤宽≤1050  ≥1051  ← 列头
        R10:    ＞1         300         200          100    0     ← 数据行
        R11:  0.5<t≤1.0    300         200           0    0
        R12:  ≤0.5           0           0            0    0
        R14:  镀锌宽度加减价          ← 下一块标题
        R15:   ＜800  800≤宽＜900  900≤宽＜1000  ≥1000
        R16:   ＞0.5    250    220    170    0
        R17:   ≤0.5    250    100     50    0
    """

    # ------------------------------------------------------------------ #
    # 厚度块（与基类布局一致，直接复用）
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        return self.find_default_thickness_blocks(sheet, steel_mill, max_col=13)

    # ------------------------------------------------------------------ #
    # 宽度块
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  块定位
    # ------------------------------------------------------------------ #

    def _first_width_col(
        self,
        sheet: Worksheet,
        header_row: int,
        start_col: int = 1,
    ) -> int | None:
        """header_row 上，从 start_col 起第一个宽度 boundary 列。"""
        for c in range(start_col, self.col_max(sheet) + 1):
            if self._is_width_boundary(self.text_or_none(sheet, header_row, c)):
                return c
        return None

    def _last_width_col(
        self,
        sheet: Worksheet,
        header_row: int,
        start_col: int,
    ) -> int:
        """header_row 上，从 start_col 起最后一个连续的宽度 boundary 列。"""
        end_col = start_col
        for c in range(start_col, self.col_max(sheet) + 1):
            if self._is_width_boundary(self.text_or_none(sheet, header_row, c)):
                end_col = c
            else:
                break
        return end_col

    def _is_width_boundary(self, text: str) -> bool:
        """判断文本是否为宽度 boundary（而非厚度单边标签）。"""
        if not text:
            return False
        text = str(text).strip()
        # 宽度 boundary 必定包含两个操作符（既有限制又有上限，或有变量名）
        return bool(_WIDTH_BOUNDARY_PATTERN.match(text))

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """定位首钢所有宽度块。

        逻辑（按你指定的）：
        1. 扫描全表，找含"宽度"关键字的行 → 块标题
        2. 标题的下一行（或往后几行）→ 找第一个含宽度 boundary 的行作为列头
        3. 块范围由相邻标题行自然确定
        4. 在块范围内，从上往下扫描确定数据起止行（遇空1行停止）
        """
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = self.col_max(sheet)

        # 1. 找所有含"宽度"关键字的行（块标题）
        w_title_rows: List[int] = []
        w_title_cols: List[int] = []
        for r in range(1, max_row + 1):
            for c in range(1, max_col + 1):
                text = self.text_or_none(sheet, r, c)
                if text and "宽度" in text:
                    w_title_rows.append(r)
                    w_title_cols.append(c)
                    break

        # 2. 遍历每个块
        for idx, (title_row, title_col) in enumerate(zip(w_title_rows, w_title_cols)):
            scan_end = w_title_rows[idx + 1] - 1 if idx + 1 < len(w_title_rows) else max_row

            # 3. 从 title_row + 1 往下，找第一个含宽度 boundary 的行作为列头行
            header_row = None
            for r in range(title_row + 1, scan_end + 1):
                for c in range(1, max_col + 1):
                    text = self.text_or_none(sheet, r, c)
                    if self._is_width_boundary(text):
                        header_row = r
                        break
                if header_row is not None:
                    break
            if header_row is None:
                continue

            # 4. 列头行上找宽度范围起止列
            width_start_col = self._first_width_col(sheet, header_row)
            if width_start_col is None:
                continue
            width_end_col = self._last_width_col(sheet, header_row, width_start_col)

            # 5. 收集价格列
            price_cols = self.collect_price_cols(
                sheet, header_row,
                start_col=width_start_col, end_col=width_end_col,
            )
            if not price_cols:
                continue

            # 6. 从上往下扫描，确定数据起止行
            # grade_col = 标题所在列（子组标签列，如 '＞1', '0.5<t≤1.0'）
            grade_col = title_col
            data_start = None
            data_end = None
            blank_streak = 0

            for r in range(header_row + 1, scan_end + 1):
                label = self.text_or_none(sheet, r, grade_col)
                has_price = any(
                    self.text_or_none(sheet, r, c) is not None for c in price_cols
                )

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

            # 7. 推断 category
            title_text = self.text_or_none(sheet, title_row, title_col) or ""
            if "镀锌" in title_text:
                category = "镀锌钢"
            elif "酸洗" in title_text:
                category = "酸洗钢"
            else:
                category = "冷轧钢"

            blocks.append({
                "category_name": category,
                "policy_type": "WIDTH",
                "header_row": header_row,
                "grade_col": grade_col,
                "price_cols": price_cols,
                "data_row_start": data_start,
                "data_row_end": data_end,
                "base_thickness": None,
                "grade_blacklist": GRADE_LABELS,
            })

        return blocks

    # ------------------------------------------------------------------ #
    #  块解析
    # ------------------------------------------------------------------ #

    def _parse_width_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: Dict[str, Any],
    ) -> List[ParsedPolicy]:
        """解析单个宽度块：每行厚度子组 → 一条政策。"""
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

            policies.append(ParsedPolicy(
                steel_mill=steel_mill,
                category_name=category_name,
                grade_type=GRADE_TYPE_WIDTH_RANGE,
                grade_value=thickness_label,
                policy_type=POLICY_TYPE_WIDTH,
                base_thickness=None,
                items=raw_items,
            ))

        return policies

    # ------------------------------------------------------------------ #
    #  入口
    # ------------------------------------------------------------------ #

    def _parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List[ParsedPolicy]:
        if policy_type == "WIDTH":
            blocks = self.find_width_blocks(sheet, steel_mill)
            policies = []
            for block in blocks:
                policies.extend(self._parse_width_block(sheet, steel_mill, block))
            return policies
        return self._parse_blocks_default(sheet, steel_mill, policy_type)
