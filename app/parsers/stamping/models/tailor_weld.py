"""
拼焊件解析领域对象

与主工艺共用同一份冲压工艺确认表（不是另一张 Excel）。
工序仍由 ``stamping_parser`` 挂在父件上；本对象只描述「哪些零件是拼焊、各片材料侧」。

判定（对照样例 烟台海众 T28）：
- 非拼焊：第 27–33 行，零件号与「长/卷料宽」都合并 7 行，行数相等。
- 拼焊：第 34–40 行，零件号合并 34–40（7 行），但卷料宽拆成 34–37 与 38–40 两块，
  任一块的融合行数 ≠ 零件融合行数。

落库对应：
- 父件 part_number = parent_part_number，is_tailor_welded=True
- 每片 TailorWeldBlankParsed → stamping_tailor_weld_blanks 一行
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class TailorWeldBlankParsed:
    """
    一片拼焊子片。

    片边界 = 该零件范围内「长/卷料宽」的一块纵向合并（样例 H34:H37 / H38:H40）。
    「宽/卷料步距」在样例中与卷料宽同切块，一并作为本片 sheet_width。

    样例 551001690AA：
    - 片1：行 34–37，长/卷料宽=550，宽/步距=465，料厚取父格 ``0.70/1.00`` 的第 1 段 0.70
    - 片2：行 38–40，长/卷料宽=555，宽/步距=465，料厚取第 2 段 1.00
    """

    blank_seq: int
    excel_row_start: int
    excel_row_end: int
    sheet_length: Decimal | None = None
    sheet_width: Decimal | None = None
    thickness: Decimal | None = None
    material: str | None = None
    blank_part_number: str | None = None
    parts_per_sheet: int | None = None
    sheet_type: str | None = None
    remark: str | None = None
    excel_sheet_name: str | None = None

    @property
    def excel_row_span(self) -> int:
        return self.excel_row_end - self.excel_row_start + 1


@dataclass(slots=True)
class TailorWeldAssemblyParsed:
    """
    一个拼焊总成（对外一个零件号）。

    样例里下列字段仍跨整个零件合并，先挂在总成上，再按片拆到 blanks：
    - material：整段一个牌号（如 HC220YD+Z），各片先复用
    - thickness_raw：``0.70/1.00``，按 ``/`` 切段，顺序对齐各片 blank_seq
    - part_weight：总成重量，不按片拆
    - parts_per_sheet / sheet_type：整段合并（如 拼焊板：见2D图）

    parent_part_number 必须与主解析 Part.part_number 一致。
    """

    parent_part_number: str
    excel_row_start: int
    excel_row_end: int
    part_name: str | None = None
    material: str | None = None
    thickness_raw: str | None = None
    part_weight: Decimal | None = None
    parts_per_sheet: int | None = None
    sheet_type: str | None = None
    blanks: list[TailorWeldBlankParsed] = field(default_factory=list)
    excel_sheet_name: str | None = None

    @property
    def blank_count(self) -> int:
        return len(self.blanks)

    @property
    def excel_row_span(self) -> int:
        return self.excel_row_end - self.excel_row_start + 1


@dataclass(slots=True)
class TailorWeldParseResult:
    """
    拼焊解析结果（与 ParserResult 并列，不混进主零件列表）。

    assemblies 仅含判定为拼焊的零件；普通件不要出现在这里。
    """

    assemblies: list[TailorWeldAssemblyParsed] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    sheet_name: str = ""
    parse_time_ms: float = 0.0

    @property
    def assembly_count(self) -> int:
        return len(self.assemblies)

    @property
    def blank_count(self) -> int:
        return sum(item.blank_count for item in self.assemblies)

    @property
    def parent_part_numbers(self) -> list[str]:
        return [item.parent_part_number for item in self.assemblies]

    def blanks_by_parent(self) -> dict[str, list[TailorWeldBlankParsed]]:
        return {item.parent_part_number: list(item.blanks) for item in self.assemblies}
