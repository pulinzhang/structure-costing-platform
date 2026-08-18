"""
零件号范围数据模型

表示 Excel 中零件号列的合并单元格范围。

因为 Excel 使用合并单元格，一个零件号会跨越多行。
例如：零件号 "501006875AA" 合并了第 5-7 行。
"""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PartNoRange:
    """
    表示零件号列的一个合并单元格范围。

    由 ExcelContext.build_merged_cache() 创建。

    由 StampingExcelParser 在解析数据行时使用，用于判断某行属于哪个零件。

    例如：
        Excel 第 5-7 行都是零件号 "501006875AA"（合并单元格）
        会生成：
            PartNoRange(value="501006875AA", start_row=5, end_row=7)
    """
    # 零件号值
    value: Any

    # 起始行号（1-based，Excel 行号）
    start_row: int

    # 结束行号（1-based，Excel 行号）
    end_row: int

    def contains(self, row: int) -> bool:
        """判断指定行是否在这个范围内"""
        return self.start_row <= row <= self.end_row

    def __repr__(self) -> str:
        return f"PartNoRange({self.value!r}, rows={self.start_row}-{self.end_row})"
