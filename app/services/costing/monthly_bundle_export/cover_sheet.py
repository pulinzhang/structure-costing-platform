"""月度核对导出 · 封皮（核价流程说明）。

视觉约定：10 列等宽栅格；主色钛灰 + 冰蓝辅色 + 极少强调红；
三级字号；流程箭头无底色；卡片浅底、弱边框。
"""

from __future__ import annotations

from typing import Any

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.workbook import Workbook

from app.common.excel_workbook import resolve_worksheet
from app.common.timezone import now

_FONT = "微软雅黑"
_SHEET_TITLE = "封皮·核价说明"
_COLS = 10

# 色板：主色钛灰 / 辅色冰蓝 / 强调红（仅总价）
_NAVY = "1A237E"
_TITAN = "37474F"
_SLATE = "546E7A"
_ICE = "E8EAF6"
_CARD = "F5F7FA"
_WHITE = "FFFFFF"
_MUTED = "78909C"
_TEXT = "263238"
_ACCENT = "C62828"
_ACCENT_SOFT = "FFEBEE"
_HINT = "FFF8E1"
_HINT_TEXT = "5D4037"
_LINE = "E0E0E0"

_FILL_NAVY = PatternFill("solid", fgColor=_NAVY)
_FILL_TITAN = PatternFill("solid", fgColor=_TITAN)
_FILL_ICE = PatternFill("solid", fgColor=_ICE)
_FILL_CARD = PatternFill("solid", fgColor=_CARD)
_FILL_WHITE = PatternFill("solid", fgColor=_WHITE)
_FILL_ACCENT = PatternFill("solid", fgColor=_ACCENT_SOFT)
_FILL_HINT = PatternFill("solid", fgColor=_HINT)
_FILL_TABLE_HEAD = PatternFill("solid", fgColor=_SLATE)
_FILL_TABLE_ZEBRA = PatternFill("solid", fgColor="ECEFF1")

_SIDE_NONE = Side(style=None)
_SIDE_HAIR = Side(style="hair", color=_LINE)
_SIDE_ACCENT = Side(style="medium", color=_NAVY)

_BORDER_CARD = Border(
    left=_SIDE_ACCENT,
    right=_SIDE_HAIR,
    top=_SIDE_HAIR,
    bottom=_SIDE_HAIR,
)
_BORDER_SOFT = Border(
    left=_SIDE_HAIR,
    right=_SIDE_HAIR,
    top=_SIDE_HAIR,
    bottom=_SIDE_HAIR,
)
_BORDER_NONE = Border(
    left=_SIDE_NONE,
    right=_SIDE_NONE,
    top=_SIDE_NONE,
    bottom=_SIDE_NONE,
)


def _font(*, size: int = 10, bold: bool = False, color: str = _TEXT) -> Font:
    return Font(name=_FONT, size=size, bold=bold, color=color)


def _paint(
    ws: Any,
    row: int,
    start: int,
    end: int,
    *,
    fill: PatternFill,
    border: Border,
) -> None:
    for col in range(start, end + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = fill
        cell.border = border


def _box(
    ws: Any,
    *,
    row: int,
    start: int,
    end: int,
    value: str,
    fill: PatternFill,
    font: Font,
    border: Border = _BORDER_SOFT,
    align: Alignment | None = None,
    height: float | None = 26,
) -> None:
    ws.merge_cells(start_row=row, start_column=start, end_row=row, end_column=end)
    cell = ws.cell(row=row, column=start, value=value)
    cell.font = font
    cell.fill = fill
    cell.alignment = align or Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = border
    _paint(ws, row, start, end, fill=fill, border=border)
    if height is not None:
        ws.row_dimensions[row].height = height


def _band(
    ws: Any,
    *,
    row: int,
    value: str,
    fill: PatternFill,
    font: Font,
    height: float = 24,
) -> None:
    _box(
        ws,
        row=row,
        start=1,
        end=_COLS,
        value=value,
        fill=fill,
        font=font,
        border=_BORDER_NONE,
        align=Alignment(horizontal="left", vertical="center", indent=1),
        height=height,
    )


def _arrow(ws: Any, row: int, text: str = "↓") -> None:
    """流程箭头：无底色、无边框，避免灰色横条打断阅读。"""
    _box(
        ws,
        row=row,
        start=1,
        end=_COLS,
        value=text,
        fill=_FILL_WHITE,
        font=_font(size=11, color=_MUTED),
        border=_BORDER_NONE,
        height=14,
    )


def _cards(
    ws: Any,
    *,
    row: int,
    items: list[str],
    font: Font,
    height: float = 32,
) -> None:
    """等宽卡片：10 列均分，每卡 2 列（5 卡）或按数量整除。"""
    count = len(items)
    span = max(1, _COLS // max(count, 1)) if count <= 0 or _COLS % count != 0 else _COLS // count
    for index, text in enumerate(items):
        start = 1 + index * span
        end = start + span - 1
        if index == count - 1:
            end = _COLS
        _box(
            ws,
            row=row,
            start=start,
            end=end,
            value=text,
            fill=_FILL_CARD,
            font=font,
            border=_BORDER_CARD,
            height=height,
        )


def write_cover_sheet(
    wb: Workbook,
    *,
    year: int,
    month: int,
    location: str,
    vehicle_model: str,
    bom_version: str | None = None,
) -> str:
    """写入月度核对导出首页封皮；返回 sheet 名。"""
    ws = resolve_worksheet(wb, _SHEET_TITLE)
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    for col in range(1, _COLS + 1):
        ws.column_dimensions[get_column_letter(col)].width = 12.5

    left = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)

    version_label = (bom_version or "").strip() or "全部版本"
    # —— 标题 / 范围 ——
    _band(
        ws,
        row=1,
        value="月度核对导出 · 成本计算说明",
        fill=_FILL_NAVY,
        font=_font(size=16, bold=True, color=_WHITE),
        height=32,
    )
    _band(
        ws,
        row=2,
        value=(
            f"{year}年{month}月　·　基地 {location}　·　项目 {vehicle_model}"
            f"　·　BOM {version_label}"
            f"　　{now().strftime('%Y-%m-%d %H:%M')}"
        ),
        fill=_FILL_ICE,
        font=_font(size=9, color=_SLATE),
        height=20,
    )
    _band(
        ws,
        row=3,
        value=(
            "【核算须知】成品总价 = 材料 + 焊接 + 间接费用。"
            "本册单价为系统最终核算快照，金额为系统计算结果；"  # <--- 明确开票依据
            "明细表仅供核对，不以 Excel 公式回算。"
            "如有疑问，请联系采购部。"
        ),
        fill=_FILL_HINT,
        font=_font(size=9, color=_HINT_TEXT),
        height=28,
    )

    # —— 一、流程 ——
    _band(
        ws,
        row=5,
        value="一、核算流程",
        fill=_FILL_TITAN,
        font=_font(size=11, bold=True, color=_WHITE),
        height=22,
    )

    _band(
        ws,
        row=6,
        value="1. 上游准备",
        fill=_FILL_ICE,
        font=_font(size=10, bold=True, color=_TITAN),
        height=20,
    )
    _cards(
        ws,
        row=7,
        items=[
            "钢材价\n钢板多少钱",
            "冲压加工费\n冲一次多少钱",
            "焊接单价\n焊一道多少钱",
            "外购 / 一口价\n外购零件价",
            "包装运输费\n进间接费用",
        ],
        font=_font(size=9, bold=True, color=_TITAN),
        height=36,
    )
    _arrow(ws, 8)
    _cards(
        ws,
        row=9,
        items=[
            "冲压零件价\n= 钢板 + 加工费（已算好）",
            "年度零件价\n外购件 / 一口价",
            "成品焊接费\n含焊接其它费用",
        ],
        font=_font(size=9, color=_TEXT),
        height=36,
    )

    _arrow(ws, 10)

    _band(
        ws,
        row=11,
        value="2. 月总账（不含间接）",
        fill=_FILL_ICE,
        font=_font(size=10, bold=True, color=_TITAN),
        height=20,
    )
    _cards(
        ws,
        row=12,
        items=["冲压件", "外购件", "一口价", "焊接费", "焊接其它"],
        font=_font(size=10, bold=True, color=_TITAN),
        height=28,
    )
    _arrow(ws, 13, "↓ 相加")
    _box(
        ws,
        row=14,
        start=1,
        end=_COLS,
        value="月总账 ＝ 冲压件 + 外购件 + 一口价 + 焊接费 + 焊接其它",
        fill=_FILL_CARD,
        font=_font(size=11, bold=True, color=_TITAN),
        border=_BORDER_CARD,
        height=28,
    )

    _arrow(ws, 15)

    _band(
        ws,
        row=16,
        value="3. 间接费用 → 成品总价",
        fill=_FILL_ICE,
        font=_font(size=10, bold=True, color=_TITAN),
        height=20,
    )
    _cards(
        ws,
        row=17,
        items=[
            "运输费",
            "仓储捆包",
            "财务 / 管理\n报废 / 利润",
            "检具分摊",
            "器具分摊",
        ],
        font=_font(size=9, bold=True, color=_TITAN),
        height=34,
    )
    _arrow(ws, 18, "↓ 月总账 + 间接")
    _box(
        ws,
        row=19,
        start=1,
        end=_COLS,
        value="成品总价 ＝ 月总账 + 间接费用合计",
        fill=_FILL_ACCENT,
        font=_font(size=12, bold=True, color=_ACCENT),
        border=Border(
            left=Side(style="medium", color=_ACCENT),
            right=_SIDE_HAIR,
            top=_SIDE_HAIR,
            bottom=_SIDE_HAIR,
        ),
        height=30,
    )

    # —— 二、原则 ——
    _band(
        ws,
        row=21,
        value="二、核心核算原则",
        fill=_FILL_TITAN,
        font=_font(size=11, bold=True, color=_WHITE),
        height=22,
    )
    principles = [
        "1. 冲压零件价已含钢板与加工费；成品侧直接引用，不再重算钢价或加工费。",
        "2. 月总账只含材料与焊接；运输、费率、分摊等列入间接费用，最后加总。",
        "3. 财务 / 管理 / 报废 / 税前利润按「该成品当月月总账」计提，不以单件直接成本为基数。",
    ]
    for offset, text in enumerate(principles):
        _box(
            ws,
            row=22 + offset,
            start=1,
            end=_COLS,
            value=text,
            fill=_FILL_HINT if offset % 2 == 0 else _FILL_WHITE,
            font=_font(size=9, color=_HINT_TEXT),
            border=_BORDER_NONE,
            align=left,
            height=22,
        )

    # —— 三、表索引 ——
    _band(
        ws,
        row=26,
        value="三、本册工作表索引",
        fill=_FILL_TITAN,
        font=_font(size=11, bold=True, color=_WHITE),
        height=22,
    )

    # 表头：3 + 7
    ws.merge_cells(start_row=27, start_column=1, end_row=27, end_column=3)
    ws.merge_cells(start_row=27, start_column=4, end_row=27, end_column=_COLS)
    for start, end, title in ((1, 3, "工作表"), (4, _COLS, "用途")):
        cell = ws.cell(row=27, column=start, value=title)
        cell.font = _font(size=9, bold=True, color=_WHITE)
        cell.fill = _FILL_TABLE_HEAD
        cell.alignment = Alignment(horizontal="center", vertical="center")
        _paint(ws, 27, start, end, fill=_FILL_TABLE_HEAD, border=_BORDER_SOFT)
    ws.row_dimensions[27].height = 18

    guide = [
        ("成品核价一览", "总结果：材料、焊接、月总账、间接、总价"),
        ("成品材料明细", "材料构成核对"),
        ("成品焊接费", "焊接费核对"),
        ("成品间接费用", "间接费用明细"),
        ("冲压核价结果", "冲压零件价来源"),
        ("冲压加工费 / 钢材联动价", "加工费、钢板价"),
        ("年度零件价 / 包装运输 / 焊接单价", "外购价、包装、焊接单价"),
    ]
    for idx, (name, meaning) in enumerate(guide):
        r = 28 + idx
        fill = _FILL_TABLE_ZEBRA if idx % 2 == 0 else _FILL_WHITE
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=_COLS)
        c1 = ws.cell(row=r, column=1, value=name)
        c1.font = _font(size=9, bold=True, color=_TITAN)
        c1.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        c2 = ws.cell(row=r, column=4, value=meaning)
        c2.font = _font(size=9, color=_SLATE)
        c2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        _paint(ws, r, 1, 3, fill=fill, border=_BORDER_SOFT)
        _paint(ws, r, 4, _COLS, fill=fill, border=_BORDER_SOFT)
        ws.row_dimensions[r].height = 18

    _band(
        ws,
        row=28 + len(guide) + 1,
        value="阅读顺序：先看「成品核价一览」，再按需查阅明细与上游表。",
        fill=_FILL_ICE,
        font=_font(size=9, color=_SLATE),
        height=20,
    )

    ws.freeze_panes = "A4"
    ws.print_title_rows = "1:2"
    return str(ws.title)
