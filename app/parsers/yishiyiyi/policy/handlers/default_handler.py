"""通用默认 Sheet 处理器。

适用排版：多个厚度块垂直堆叠（冷轧 / 镀锌 / 酸洗）。
子类只需覆写 find_thickness_blocks / find_width_blocks，
基类负责块 → ParsedPolicy 的通用解析。

块结构:
    [钢种列]  [厚度列1] [厚度列2] ... [厚度列N]
    DC01       180       140       ...
"""

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.handlers.base_handler.base_handler import (
    BaseSheetHandler,
)
from app.parsers.yishiyiyi.policy.models.policy_block import PolicyBlock


class DefaultSheetHandler(BaseSheetHandler):
    """默认 Sheet 处理器（厚度块垂直堆叠）。"""

    # ------------------------------------------------------------------ #
    # 厚度块查找 - 复用基类的默认扫描
    # ------------------------------------------------------------------ #

    def find_thickness_blocks(self, sheet: Worksheet, steel_mill: str) -> list[PolicyBlock]:
        return self.find_default_thickness_blocks(sheet, steel_mill)

    # ------------------------------------------------------------------ #
    # 宽度块查找（默认无）
    # ------------------------------------------------------------------ #

    def find_width_blocks(self, _sheet: Worksheet, _steel_mill: str) -> list[PolicyBlock]:
        return []
