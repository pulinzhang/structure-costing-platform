"""马钢 Sheet 处理器（旧版格式，固定区域 N2:T30）。

六类宽度加减价区域（写死固定行）：
    冷轧钢卷宽度加减价              header_row=3   data_row=4~5    col N(14)-R(18)
    冷轧卷板（非高强）    header_row=9   data_row=10~11  col N(14)-T(20)
    冷轧卷板（高强）      header_row=13  data_row=14      col N(14)-S(19)
    镀锌卷板（非高强）    header_row=22  data_row=23      col N(14)-S(19)
    镀锌卷板（高强）      header_row=26  data_row=27      col N(14)-S(19)
    镀锌卷板（高强）      header_row=29  data_row=30      col N(14)-S(19)

第三类，冷轧卷板（高强）宽度范围是特殊格式：
    列头文本 <900 <1000 1000≤w<1400 1400≤w<1500 ≥1500
    其中"<900"表示 w<900，"<1000"实际是 900≤w<1000，"≥1000"实际是 w≥1000
    因此 col15~col19 的真实边界为：col15(900≤w<1000) col16(w≥1000) col17(1000≤w<1400) col18(1400≤w<1500) col19(w≥1500)

闭区间用"～"表示，如 0.3～3.0 表示 0.3<=t<=3.0

宽度区域解析见 magang_width.py，厚度见 magang_thickness.py。
对外仍从此文件导入 MagangSheetHandler。
"""

from decimal import Decimal
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.handlers.base_handler.base_handler import (
    BaseSheetHandler,
)
from app.parsers.yishiyiyi.policy.models.ladder_item import ParsedLadderItem

from .magang_thickness import parse_thickness_fixed
from .magang_width import _WidthRegion, build_width_items, parse_one_region, parse_width_fixed


class MagangSheetHandler(BaseSheetHandler):
    """马钢 Sheet 处理器（旧版格式）。使用固定区域逐行读取 N2:T33 六类宽度加减价。"""

    def parse(
        self,
        sheet: Worksheet,
        steel_mill: str,
        warnings: list[str],
    ) -> list[Any]:
        policies: list[Any] = []
        policies.extend(self._parse_thickness_fixed(sheet, steel_mill))
        return policies

    def _parse_width_fixed(
        self, sheet: Worksheet, steel_mill: str, warnings: list[str]
    ) -> list[Any]:
        return parse_width_fixed(sheet, steel_mill, warnings)

    def _parse_one_region(
        self,
        sheet: Worksheet,
        steel_mill: str,
        region: _WidthRegion,
        warnings: list[str],
    ) -> list[Any]:
        return parse_one_region(sheet, steel_mill, region, warnings)

    def _build_width_items(
        self,
        sheet: Worksheet,
        row: int,
        price_cols: list[int],
        boundaries: dict[int, tuple[Decimal | None, str, Decimal | None, str]],
    ) -> list[ParsedLadderItem]:
        return build_width_items(sheet, row, price_cols, boundaries)

    def _parse_thickness_fixed(self, sheet: Worksheet, steel_mill: str) -> list[Any]:
        return parse_thickness_fixed(self, sheet, steel_mill)
