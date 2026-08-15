"""鞍钢集团 Sheet 处理器。

排版特点:
- 左侧（cols 1-10）：单一厚度块，共用 header
- 右侧（cols 17+）：3 个宽度子块（冷轧/镀锌/酸洗），
  每块从标题行（含类别关键字）开始，到下一个类别标题 - 1

复用基类的 locate_thickness_block 处理左侧厚度，
find_width_blocks 处理右侧 3 个宽度块。

宽度加价逻辑（与厚度无关）:
- 宽度加价按钢材类别（冷轧钢/镀锌钢/酸洗钢）划分，不区分钢种牌号
- 每个类别块只生成一条政策，grade_value = category_name，grade_type = CATEGORY
- 每行数据（各钢种）共用相同的宽度阶梯价格（合并单元格实现）
"""
from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.handlers.base_handler import BaseSheetHandler
from .constants import GRADE_LABELS


# 鞍钢集团宽度块：标题列 = 17（Q 列），列头行 = 标题行 + 1
_W_TITLE_COL = 17
_W_HEADER_COL = 17  # "宽度mm" 在 title_row 的同一列
_CATEGORY_KEYWORDS = (
    ("冷轧产品", "冷轧钢"),
    ("镀锌产品", "镀锌钢"),
    ("酸洗产品", "酸洗钢"),
)


class AngangSheetHandler(BaseSheetHandler):
    """鞍钢集团 Sheet 处理器。"""

    # ------------------------------------------------------------------ #
    # 厚度块
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """左侧（cols 1-10）：多块厚度 (冷轧/镀锌/酸洗 三个)."""
        return self.find_default_thickness_blocks(sheet, steel_mill)

    # ------------------------------------------------------------------ #
    # 宽度块：鞍钢专用解析（按类别生成政策，与厚度无关）
    # ------------------------------------------------------------------ #

    def _parse_angang_width_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: Dict[str, Any],
    ) -> List:
        """鞍钢宽度块解析：每个类别块生成一条政策，grade_value = category_name。

        鞍钢宽度加价按钢材类别（冷轧钢/镀锌钢/酸洗钢）划分，不区分钢种牌号。
        每行数据（各钢种）共用相同的宽度阶梯价格（合并单元格实现）。
        因此每块只生成一条政策，grade_type = CATEGORY，所有宽度区间作为 items。
        """
        from ..models import ParsedPolicy
        from ..models.policy import GRADE_TYPE_CATEGORY, POLICY_TYPE_WIDTH

        header_row = block["header_row"]
        price_cols = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")

        boundaries = self._collect_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        sorted_price_cols = sorted(price_cols)

        # 从第一行数据读取价格（合并单元格的首个单元格值）
        items, _ = self._build_items_for_row(
            sheet, data_start, sorted_price_cols, boundaries, POLICY_TYPE_WIDTH, sort_order=0
        )
        if not items:
            return []

        # 每块只生成一条政策，grade_type = CATEGORY，grade_value = category_name
        return [
            ParsedPolicy(
                steel_mill=steel_mill,
                category_name=category_name,
                grade_type=GRADE_TYPE_CATEGORY,
                grade_value=category_name,
                policy_type=POLICY_TYPE_WIDTH,
                base_thickness=None,
                items=items,
            )
        ]

    def _parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List:
        """鞍钢定制：WIDTH 政策走专用解析（按类别生成，每类别一条）。"""
        if policy_type == "WIDTH":
            blocks = self.find_width_blocks(sheet, steel_mill)
            policies = []
            for block in blocks:
                policies.extend(self._parse_angang_width_block(sheet, steel_mill, block))
            return policies
        # THICKNESS 政策走通用解析
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
    # 宽度块
    # ------------------------------------------------------------------ #

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """右侧（cols 17+）：3 个宽度子块（冷轧/镀锌/酸洗）。

        标题在 col 17（R4=`冷轧产品宽度加价`，R8=`镀锌...`，R12=`酸洗...`）。
        列头行 = 标题行 + 1，列头列 = 17。
        """
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = self.col_max(sheet)

        # 收集所有宽度块起始行（col 17 含"宽度加价"）
        block_starts: List[int] = []
        for r in range(1, max_row + 1):
            text = self.text(sheet, r, _W_TITLE_COL)
            if text and "宽度" in text and "加价" in text:
                block_starts.append(r)

        for i, title_row in enumerate(block_starts):
            # 该块结束 = 下一个块标题 - 1；若没有下一标题，则用 find_block_end_row
            if i + 1 < len(block_starts):
                block_end = block_starts[i + 1] - 1
            else:
                block_end = self.find_block_end_row(
                    sheet, title_row + 2, max_row, max_col
                )
            # 再一次避免吸入后面 "钢种" label_row
            next_label_rows = self.find_grade_label_rows(sheet, title_row + 2, max_row)
            if next_label_rows:
                block_end = min(block_end, next_label_rows[0] - 1)
            # 避免吸入后面的"厚度加减价"段标题
            next_break = self.find_section_break_row(
                sheet, title_row + 2, max_row, scan_col=1
            )
            if next_break is not None:
                block_end = min(block_end, next_break - 1)

            # 列头行 = 标题行 + 1
            header_row = title_row + 1
            if header_row > block_end:
                continue

            # 推断 category
            title_text = self.text(sheet, title_row, _W_TITLE_COL)
            category = "冷轧钢"
            for kw, cat in _CATEGORY_KEYWORDS:
                if kw in title_text:
                    category = cat
                    break

            # 宽度边界列（从 col 18 起）
            price_cols = self.collect_price_cols(
                sheet, header_row, start_col=_W_HEADER_COL + 1, end_col=max_col
            )
            if not price_cols:
                continue

            blocks.append({
                "category_name": category,
                "policy_type": "WIDTH",
                "grade_col": 1,
                "header_row": header_row,
                "price_cols": price_cols,
                "data_row_start": header_row + 1,
                "data_row_end": block_end,
                "base_thickness": None,
                "grade_blacklist": GRADE_LABELS,
            })

        return blocks
