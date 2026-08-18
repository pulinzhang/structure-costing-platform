"""通用默认 Sheet 处理器。

适用排版：多个厚度块垂直堆叠（冷轧 / 镀锌 / 酸洗）。
子类只需覆写 find_thickness_blocks / find_width_blocks，
基类负责块 → ParsedPolicy 的通用解析。

块结构:
    [钢种列]  [厚度列1] [厚度列2] ... [厚度列N]
    DC01       180       140       ...
"""

from typing import Any, Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.handlers.base_handler import BaseSheetHandler


class DefaultSheetHandler(BaseSheetHandler):
    """默认 Sheet 处理器（厚度块垂直堆叠）。"""

    # ------------------------------------------------------------------ #
    # 厚度块查找 - 复用基类的默认扫描
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        return self.find_default_thickness_blocks(sheet, steel_mill)

    # ------------------------------------------------------------------ #
    # 宽度块查找（默认无）
    # ------------------------------------------------------------------ #

    def find_width_blocks(
        self, sheet: Worksheet, steel_mill: str
    ) -> List[Dict[str, Any]]:
        return []
