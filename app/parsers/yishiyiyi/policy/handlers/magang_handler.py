"""马钢 Sheet 处理器（旧版格式）。

只导入厚度加减价。宽度加减价本期不导入。
对外仍从此文件导入 MagangSheetHandler。
"""

from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.handlers.base_handler.base_handler import (
    BaseSheetHandler,
)

from .magang_thickness import parse_thickness_fixed


class MagangSheetHandler(BaseSheetHandler):
    """马钢 Sheet 处理器（旧版格式）。只导入厚度加减价。"""

    def parse(
        self,
        sheet: Worksheet,
        steel_mill: str,
        _warnings: list[str],
    ) -> list[Any]:
        policies: list[Any] = []
        policies.extend(self._parse_thickness_fixed(sheet, steel_mill))
        return policies

    def _parse_thickness_fixed(self, sheet: Worksheet, steel_mill: str) -> list[Any]:
        return parse_thickness_fixed(self, sheet, steel_mill)
