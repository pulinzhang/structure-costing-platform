"""首钢 Sheet 处理器。

排版特点:
- 厚度块垂直堆叠（冷轧/镀锌），左侧 cols 1-13
- 宽度块跟在厚度块同一行范围的右侧（col 14 起，含宽度标题 "宽度加减价"）

数据布局示例:
    R4: 钢种 厚度加减价,基准厚度1.0——元/吨 ...   冷轧宽度加减价   (col 14)
    R5:        ≤0.5  ≤0.6  ≤0.7 ...               <1500  <1600  ...
    R6: DC01   210   180   140 ...                180    300   ...

冷轧宽度加减价
	700≤宽＜800	 800≤宽＜900	900≤宽≤1050	≥1051
    ＞1	300	200	100	0
    0.5<t≤1.0	300	200	0	0
    ≤0.5	0	0	0	0

    镀锌宽度加减价
        ＜800	800≤宽＜900	900≤宽＜1000	≥1000
    ＞0.5	250	220	170	0
    ≤0.5	250	100	50	0


"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from openpyxl.worksheet.worksheet import Worksheet

from .base_handler import BaseSheetHandler
from .constants import GRADE_LABELS, parse_thickness_label
from ..models.policy import GRADE_TYPE_WIDTH_RANGE, POLICY_TYPE_WIDTH


_W_GRADE_COL = 14  # N 列（钢种列）
_W_START_COL = 15  # O 列起为宽度边界列


class ShougangSheetHandler(BaseSheetHandler):
    """首钢 Sheet 处理器。"""

    # ------------------------------------------------------------------ #
    # 厚度块：复用基类 locate_thickness_block
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """首钢厚度块与默认布局相同：label_row 在 col 1，max_col=13。"""
        return self.find_default_thickness_blocks(sheet, steel_mill, max_col=13)

    # ------------------------------------------------------------------ #
    # 宽度块
    # ------------------------------------------------------------------ #

    def _find_thickness_subgroup_rows_in_range(
        self,
        sheet: Worksheet,
        start_row: int,
        end_row: int,
        label_col: int,
    ) -> List[int]:
        """在 [start_row, end_row] 范围内，找所有厚度子组标记行。

        首钢宽度块的 col 14 不是钢种列，而是厚度子组标记（如 '＞1', '0.5<t≤1.0'）。
        这些标记定义了块的行范围：标题行 → 最后一条子组标记行。
        """
        rows = []
        for r in range(start_row, end_row + 1):
            raw_val = sheet.cell(row=r, column=label_col).value
            if raw_val is not None:
                val = str(raw_val).strip()
                if val:
                    rows.append(r)
            elif self.find_start_row(sheet, r, label_col) is not None:
                rows.append(r)
        return rows

    # ------------------------------------------------------------------ #
    # 宽度块解析（首钢专用：按厚度子组行生成政策）
    # ------------------------------------------------------------------ #

    def _parse_shougang_width_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: Dict[str, Any],
    ) -> List:
        """首钢宽度块解析：每行厚度子组生成一条政策。

        块的列头行（header_row）含宽度边界，如 '700≤宽＜800'。
        每行数据行的 grade_col 存储厚度子组名（如 '＞1', '0.5<t≤1.0'）。
        """
        from ..models import ParsedPolicy
        from ..models.policy import GRADE_TYPE_WIDTH_RANGE

        header_row = block["header_row"]
        price_cols = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")

        boundaries = self._collect_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        sorted_price_cols = sorted(price_cols)
        policies = []

        for r in range(data_start, data_end + 1):
            # 首钢宽度块：col 14 存厚度子组名
            thickness_label = self.text_or_none(sheet, r, _W_GRADE_COL)
            if not thickness_label or thickness_label in GRADE_LABELS:
                continue

            # 先构建仅有宽度维度的 items，再补充厚度子组上下文
            raw_items = self._build_items_for_row(
                sheet, r, sorted_price_cols, boundaries, POLICY_TYPE_WIDTH, sort_order=r
            )
            if not raw_items:
                continue

            # 解析厚度标签得到具体边界值
            thick_min_raw, thick_min_op, thick_max_raw, thick_max_op = parse_thickness_label(
                thickness_label
            )
            thick_min = Decimal(str(thick_min_raw)) if thick_min_raw is not None else None
            thick_max = Decimal(str(thick_max_raw)) if thick_max_raw is not None else None

            # 补充 target_sub_group（厚度子组名）和厚度维度
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

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """首钢宽度块定位。

        布局特点：
        - 行 4: '冷轧宽度加减价' 标题（col 14）
        - 行 5: 宽度边界列头（cols 15-18）：'700≤宽＜800' 等
        - 行 6-8: 厚度子组标记（col 14）：'＞1', '0.5<t≤1.0', '≤0.5'
                  价格数据在 cols 15-18
        - 行 10: '镀锌宽度加减价' 下一块标题

        识别方式：
        1. 找 col 14 含"宽度"字样的标题行
        2. 向下扫描该列，找到所有厚度子组标记行
        3. 最后一个子组标记行即为 block_end
        """
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = self.col_max(sheet)

        if max_col < _W_START_COL:
            return []

        # 找所有 col 14 含"宽度"字样的标题行
        w_title_rows: List[int] = []
        for r in range(1, max_row + 1):
            text = self.text(sheet, r, _W_GRADE_COL)
            if text and "宽度" in text:
                w_title_rows.append(r)

        for i, title_row in enumerate(w_title_rows):
            # 块范围：下一个 title_row - 1（若有），否则 max_row
            if i + 1 < len(w_title_rows):
                scan_end = w_title_rows[i + 1] - 1
            else:
                scan_end = max_row

            # 找本块所有厚度子组标记行
            subgroup_rows = self._find_thickness_subgroup_rows_in_range(
                sheet, title_row + 1, scan_end, _W_GRADE_COL,
            )
            if not subgroup_rows:
                continue

            block_end = subgroup_rows[-1]
            if block_end <= title_row + 1:
                continue

            # 推断 category（按标题含"镀锌"还是"酸洗"）
            title_text = self.text(sheet, title_row, _W_GRADE_COL)
            if "镀锌" in title_text:
                category = "镀锌钢"
            elif "酸洗" in title_text:
                category = "酸洗钢"
            else:
                category = "冷轧钢"

            # 收集价格列（cols 15+ 的非空数值列）
            price_cols = self.collect_price_cols(
                sheet, title_row + 1,
                start_col=_W_START_COL, end_col=min(max_col, 18),
            )
            if not price_cols:
                continue

            # 数据起始行 = 第一个子组标记行
            data_start = subgroup_rows[0]

            blocks.append({
                "category_name": category,
                "policy_type": "WIDTH",
                "grade_col": None,
                "header_row": title_row + 1,  # 列头行含宽度边界
                "price_cols": price_cols,
                "data_row_start": data_start,
                "data_row_end": block_end,
                "base_thickness": None,
                "grade_blacklist": GRADE_LABELS,
            })

        return blocks

    def _parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List:
        """首钢定制：WIDTH 政策走专用解析（按厚度子组行生成）。"""
        if policy_type == "WIDTH":
            blocks = self.find_width_blocks(sheet, steel_mill)
            policies = []
            for block in blocks:
                policies.extend(self._parse_shougang_width_block(sheet, steel_mill, block))
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