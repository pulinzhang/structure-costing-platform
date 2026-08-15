"""鞍神 Sheet 处理器。

排版特点（鞍钢神钢厚度加减价）:
- 不分钢种，通用厚度-宽度组合加价
- Row 5: 标题行 "Thicknss(mm)" | "Width(mm)"
- Row 6: 宽度范围 "750＜W≤1250"
- Row 7-10: 厚度范围 | 加价数值

数据示例:
    Thicknss(mm)    Width(mm)
                     750＜W≤1250
    2.0＜T≤2.3      300
    1.6＜T≤2.0      200
    1.0≤T≤1.6      0
    0.75≤T＜1.0     380
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from openpyxl.worksheet.worksheet import Worksheet
from ..value_parser import _to_int_price

from app.parsers.yishiyiyi.policy.handlers.base_handler import BaseSheetHandler
from .constants import parse_thickness_label


class AnshenSheetHandler(BaseSheetHandler):
    """鞍神 Sheet 处理器（厚度-宽度组合加价）。"""

    def parse(self, sheet: Worksheet, steel_mill: str, warnings: list) -> list:
        """鞍神：厚度-宽度组合加价，只走 THICKNESS_WIDTH 通道。"""
        return self._parse_blocks(sheet, steel_mill, "THICKNESS_WIDTH")

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        return []

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        """定位鞍神规格加价表格。

        表格结构（从 Row 5 开始）:
        - Row 5 (header): "Thicknss(mm)" | "Width(mm)"
        - Row 6 (boundary): 空 | "750＜W≤1250"
        - Row 7-10 (data): 厚度范围 | 价格

        只有一个宽度范围块。
        """
        blocks: List[Dict[str, Any]] = []
        max_row = self.row_max(sheet)
        max_col = self.col_max(sheet)

        # 找"鞍神规格加价"关键字所在行
        header_row: Optional[int] = None
        for r in range(1, max_row + 1):
            text = self.text(sheet, r, 1)
            if text and "鞍神规格加价" in text:
                header_row = r
                break

        if header_row is None:
            return []

        # "Thicknss(mm)" 标题在下一行
        title_row = header_row + 1

        # 找数据起始行（厚度范围行）
        data_start: Optional[int] = None
        for r in range(title_row + 1, max_row + 1):
            val = self.text(sheet, r, 1)
            if val and val.strip():
                # 检查是否是厚度范围格式（如 "2.0＜T≤2.3"）
                if "＜" in val or "<" in val or "≤" in val or ">=" in val:
                    data_start = r
                    break

        if data_start is None:
            return []

        # 找数据结束行（连续空行或超出表格范围）
        data_end = data_start
        for r in range(data_start + 1, max_row + 1):
            val = self.text(sheet, r, 1)
            if val and val.strip():
                data_end = r
            else:
                # 连续空行超过 BLANK_LIMIT 则停止
                empty_count = 0
                for rr in range(r, min(r + 3, max_row + 1)):
                    if not self.text(sheet, rr, 1):
                        empty_count += 1
                    else:
                        break
                if empty_count >= 2:
                    break
                data_end = r

        # 宽度边界行在 title_row + 1
        width_boundary_row = title_row + 1

        # 收集价格列：B 列（宽度边界在 B 列，C 列是价格数据）
        # 实际上价格就在 B 列，B 列是 750＜W≤1250
        # 数据列应该是 B 列（第2列）
        price_col = 2  # B 列

        block: Dict[str, Any] = {
            "category_name": "冷轧钢",
            "policy_type": "THICKNESS_WIDTH",
            "grade_col": 1,
            "header_row": width_boundary_row,
            "price_cols": [price_col],
            "data_row_start": data_start,
            "data_row_end": data_end,
            "base_thickness": None,
        }
        blocks.append(block)
        return blocks

    def _parse_blocks(
        self,
        sheet: Worksheet,
        steel_mill: str,
        policy_type: str,
    ) -> List:
        """鞍神定制：所有政策走专用解析。"""
        if policy_type == "THICKNESS_WIDTH":
            blocks = self.find_width_blocks(sheet, steel_mill)
            policies: List = []
            for block in blocks:
                policies.extend(self._parse_anshen_block(sheet, steel_mill, block))
            return policies
        return []

    def _parse_anshen_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: Dict[str, Any],
    ) -> List:
        """解析鞍神宽度块：每行厚度范围生成一条政策。

        鞍神不分钢种，同一宽度范围内按厚度范围分行。
        grade_type=GRADE（不分类），grade_value=厚度范围标签（如 "1.6＜T≤2.0"），
        items 只包含宽度边界和价格。不同厚度范围通过 grade_value 区分。
        """
        from ..models import ParsedPolicy
        from ..models.policy import (
            GRADE_TYPE_THICKNESS_RANGE,
            POLICY_TYPE_THICKNESS_WIDTH,
        )

        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")

        # 宽度边界在 header_row，B 列
        header_row = block["header_row"]
        width_boundary = self.text(sheet, header_row, 2) or "750＜W≤1250"

        policies: List = []

        for r in range(data_start, data_end + 1):
            thickness_label = self.text(sheet, r, 1)
            if not thickness_label or not thickness_label.strip():
                continue

            # 解析厚度范围
            thick_min_raw, thick_min_op, thick_max_raw, thick_max_op = parse_thickness_label(
                thickness_label
            )
            thick_min = Decimal(str(thick_min_raw)) if thick_min_raw is not None else None
            thick_max = Decimal(str(thick_max_raw)) if thick_max_raw is not None else None

            # 解析宽度范围
            width_min_raw, width_min_op, width_max_raw, width_max_op = self._parse_width_boundary(
                width_boundary
            )
            width_min = Decimal(str(width_min_raw)) if width_min_raw is not None else None
            width_max = Decimal(str(width_max_raw)) if width_max_raw is not None else None

            # 读取价格
            price_raw = sheet.cell(row=r, column=2).value
            if price_raw is None:
                continue

            price = _to_int_price(price_raw)

            # 构建 LadderItem
            from ..models.policy import ParsedLadderItem

            item = ParsedLadderItem(
                width_min=width_min,
                width_min_operator=width_min_op or ">=",
                width_max=width_max,
                width_max_operator=width_max_op or "<",
                thick_min=thick_min,
                thick_min_operator=thick_min_op or ">=",
                thick_max=thick_max,
                thick_max_operator=thick_max_op or "<",
                price_adjustment=price,
                sort_order=r,
                excel_row=r,
                excel_col=2,
            )

            # grade_value = 厚度范围标签（如 "1.6＜T≤2.0"）
            # grade_type = THICKNESS_RANGE（以厚度范围区分，不分钢种）
            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=category_name,
                    grade_type=GRADE_TYPE_THICKNESS_RANGE,
                    grade_value=thickness_label.strip(),
                    policy_type=POLICY_TYPE_THICKNESS_WIDTH,
                    base_thickness=None,
                    items=[item],
                )
            )

        return policies

    def _parse_width_boundary(self, boundary: str) -> tuple:
        """解析宽度边界字符串，返回 (min, min_op, max, max_op)。

        支持格式：
        - "750＜W≤1250"
        - "W≤1250"
        - "W>750"
        """
        import re

        # 提取最小值和操作符
        min_val: Optional[float] = None
        min_op: str = ">="
        max_val: Optional[float] = None
        max_op: str = "<"

        # 匹配 "X＜W≤Y" 或 "X<W<=Y" 格式
        m = re.match(
            r"(\d+(?:\.\d+)?)\s*[＜<]\s*W\s*[≤<=]\s*(\d+(?:\.\d+)?)",
            boundary,
            re.IGNORECASE,
        )
        if m:
            min_val = float(m.group(1))
            max_val = float(m.group(2))
            min_op = ">"
            max_op = "<="
            return min_val, min_op, max_val, max_op

        # 匹配 "W≤Y" 或 "W<=Y" 格式（只有上界）
        m = re.match(r"W\s*[≤<=]\s*(\d+(?:\.\d+)?)", boundary, re.IGNORECASE)
        if m:
            max_val = float(m.group(1))
            max_op = "<="
            return None, ">=", max_val, max_op

        # 匹配 "W＞X" 或 "W>X" 格式（只有下界）
        m = re.match(r"W\s*[＞>]\s*(\d+(?:\.\d+)?)", boundary, re.IGNORECASE)
        if m:
            min_val = float(m.group(1))
            min_op = ">"
            return min_val, min_op, None, "<"

        return None, ">=", None, "<"
