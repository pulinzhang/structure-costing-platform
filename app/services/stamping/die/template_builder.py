"""冲压模具布点导入模板：A～AD（套数后插入模具编号）。"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

COL_COUNT = 30  # A～AD，第 17 列为模具编号
DATA_START_ROW = 6
_FONT_NAME = "宋体"
_THIN = Border(
    left=Side(style="thin", color="000000"),
    right=Side(style="thin", color="000000"),
    top=Side(style="thin", color="000000"),
    bottom=Side(style="thin", color="000000"),
)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_HEADER_FONT = Font(name=_FONT_NAME, size=12)
_TITLE_FONT = Font(name=_FONT_NAME, size=18, bold=True)
_META_FONT = Font(name=_FONT_NAME, size=16)
_DATA_FONT = Font(name=_FONT_NAME, size=12)
_NOTE_TITLE_FONT = Font(name=_FONT_NAME, size=12, bold=True)
_NOTE_FONT = Font(name=_FONT_NAME, size=10)

_ALLOC_NOTES = (
    "【模具费分摊说明】上传只读上方表格，不读本段。",
    "1. 先选采购基地并填写项目（新项目在本页填写）。模具方式或生产方式含「双槽 / 合并 / 一出二」→ 各序默认分摊 0.50；否则 1.00（单干）。左右件各记一半，避免同一副模记两次。",
    "2. 共模件若第一序单独开模（常见落料），上传后到模具清单把该序比例改成 1，后面共模序保持 0.50。",
    "3. 级进模写在生产方式。模具费不打 0.80（那是加工费折扣）。级进且共模仍是 0.50。",
    "4. 模具编号可空，系统按 DP-40-项目-流水自动补号；已填写的编号保持不变。",
    "5. 预估重量（T）= 长×宽×高×掏空×7.85÷10⁹。工序费 = 重量 × 单价 × 分摊比例 ÷ 分摊万台。",
)

_WIDTHS = [
    6,
    15,
    30,
    14,
    12,
    9,
    9,
    8,
    10,
    12,
    8,
    10,
    12,
    12,
    12,
    8,
    16,
    12,
    10,
    10,
    10,
    12,
    12,
    11,
    10,
    12,
    12,
    12,
    10,
    28,
]

_HEADER_MERGES = (
    (3, 1, 5, 1),
    (3, 2, 3, 7),
    (3, 8, 3, 30),
    (4, 2, 5, 2),
    (4, 3, 5, 3),
    (4, 4, 5, 4),
    (4, 5, 5, 5),
    (4, 6, 5, 6),
    (4, 7, 5, 7),
    (4, 8, 4, 9),
    (4, 10, 5, 10),
    (4, 11, 5, 11),
    (4, 12, 5, 12),
    (4, 13, 5, 13),
    (4, 14, 4, 16),
    (4, 17, 5, 17),
    (4, 18, 4, 20),
    (4, 21, 5, 21),
    (4, 22, 5, 22),
    (4, 23, 5, 23),
    (4, 24, 5, 24),
    (4, 25, 5, 25),
    (4, 26, 5, 26),
    (4, 27, 5, 27),
    (4, 28, 5, 28),
    (4, 29, 5, 29),
    (4, 30, 5, 30),
)

_PART_COLS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 23, 25, 26, 27, 28, 29, 30)


def _active_worksheet(workbook: Workbook, title: str) -> Worksheet:
    sheet = workbook.active
    if not isinstance(sheet, Worksheet):
        sheet = workbook.create_sheet(title)
    sheet.title = title
    return sheet


def build_die_layout_template() -> tuple[bytes, str]:
    workbook = Workbook()
    sheet = _active_worksheet(workbook, "零件汇总")
    _write_banner(sheet)
    _write_headers(sheet)
    last_row = _write_sample(sheet)
    last_row = _write_alloc_notes(sheet, last_row)
    _apply_layout(sheet, last_row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue(), "冲压模具布点导入模板.xlsx"


def _write_banner(sheet: Worksheet) -> None:
    sheet.merge_cells(start_row=1, start_column=1, end_row=2, end_column=27)
    title = sheet.cell(row=1, column=1, value="T13J项目冲压模具布点工艺清单")
    title.font = _TITLE_FONT
    title.alignment = _CENTER

    sheet.merge_cells(start_row=1, start_column=28, end_row=2, end_column=29)
    version_label = sheet.cell(row=1, column=28, value="版本")
    version_label.font = _META_FONT
    version_label.alignment = _CENTER

    sheet.merge_cells(start_row=1, start_column=30, end_row=2, end_column=30)
    version_value = sheet.cell(row=1, column=30, value="V0-01")
    version_value.font = _META_FONT
    version_value.alignment = _CENTER

    sheet.row_dimensions[1].height = 33
    sheet.row_dimensions[2].height = 28


def _write_headers(sheet: Worksheet) -> None:
    for start_row, start_col, end_row, end_col in _HEADER_MERGES:
        sheet.merge_cells(
            start_row=start_row,
            start_column=start_col,
            end_row=end_row,
            end_column=end_col,
        )

    sheet.cell(row=3, column=1, value="序号")
    sheet.cell(row=3, column=2, value="产品信息")
    sheet.cell(row=3, column=8, value="工艺清单")

    row4 = {
        2: "零件号",
        3: "零件名称",
        4: "简图",
        5: "材质",
        6: "料厚\n（mm）",
        7: "净重\n（kg）",
        8: "预估板料尺寸（mm）",
        10: "板料形状",
        11: "可制件数",
        12: "预估单件材料消耗（KG）",
        13: "预估单件材料利用率",
        14: "预估工艺",
        17: "模具编号",
        18: "预估模具尺寸（mm*mm*mm）",
        21: "掏空系数",
        22: "预估重量\n（T）",
        23: "预估重量小计\n（T）",
        24: "使用设备吨位（T）",
        25: "模具类型",
        26: "模具方式",
        27: "生产方式",
        28: "是否需要端拾器",
        29: "零件等级",
        30: "备注",
    }
    row5 = {
        8: "长",
        9: "宽",
        14: "工序名称",
        15: "工序",
        16: "套数",
        18: "长度",
        19: "宽度",
        20: "高度",
    }
    for col, value in row4.items():
        sheet.cell(row=4, column=col, value=value)
    for col, value in row5.items():
        sheet.cell(row=5, column=col, value=value)

    for row in range(1, 6):
        sheet.row_dimensions[row].height = {1: 33, 2: 28, 3: 36, 4: 30, 5: 57}[row]
        for col in range(1, COL_COUNT + 1):
            cell = sheet.cell(row=row, column=col)
            if row <= 2 and col == 1:
                cell.font = _TITLE_FONT
            elif row <= 2:
                cell.font = _META_FONT
            else:
                cell.font = _HEADER_FONT
            cell.alignment = _CENTER
            cell.border = _THIN


def _write_sample(sheet: Worksheet) -> int:
    start_row = DATA_START_ROW
    processes = (
        ("OP05", "BL", 1, "DP-40-T13J-001", 880, 850, 350, 0.65, 1.3361, 250),
        ("OP10", "FO", 1, "DP-40-T13J-002", 650, 400, 320, 0.65, 0.5348, 160),
        ("OP20", "FL", 1, "DP-40-T13J-003", 650, 400, 340, 0.65, 0.5682, 160),
        ("OP30", "FO+RST", 1, "DP-40-T13J-004", 640, 380, 380, 0.65, 0.6054, 200),
        ("OP40", "PI+CPI", 1, "DP-40-T13J-005", 850, 380, 380, 0.65, 0.8041, 200),
    )
    n_rows = len(processes)
    end_row = start_row + n_rows - 1

    for offset in range(n_rows):
        excel_row = start_row + offset
        sheet.row_dimensions[excel_row].height = 18.75
        for col in range(1, COL_COUNT + 1):
            cell = sheet.cell(row=excel_row, column=col)
            cell.font = _DATA_FONT
            cell.alignment = _CENTER
            cell.border = _THIN

    for col in _PART_COLS:
        if end_row > start_row:
            sheet.merge_cells(
                start_row=start_row,
                start_column=col,
                end_row=end_row,
                end_column=col,
            )

    sheet.cell(row=start_row, column=1, value=1)
    sheet.cell(row=start_row, column=2, value="502007709AA")
    sheet.cell(row=start_row, column=3, value="左后尾灯上安装板")
    sheet.cell(row=start_row, column=5, value="DC56D+Z")
    sheet.cell(row=start_row, column=6, value=0.65)
    sheet.cell(row=start_row, column=7, value=0.1639)
    sheet.cell(row=start_row, column=8, value=880)
    sheet.cell(row=start_row, column=9, value=850)
    sheet.cell(row=start_row, column=10, value="利用侧围废料")
    sheet.cell(row=start_row, column=11, value=1)
    sheet.cell(row=start_row, column=12, value=0.5)
    utilization = sheet.cell(row=start_row, column=13, value=0.65)
    utilization.number_format = "0.00%"
    sheet.cell(row=start_row, column=25, value="钢板模")
    sheet.cell(row=start_row, column=26, value="双槽")
    sheet.cell(row=start_row, column=27, value="手工线")
    sheet.cell(row=start_row, column=29, value="C")
    sheet.cell(
        row=start_row, column=30, value="模板样例，请按布点清单填写；简图列不导入；模具编号可空"
    )

    subtotal = 0.0
    for offset, item in enumerate(processes):
        excel_row = start_row + offset
        seq, code, die_sets, die_number, length, width, height, hollow, weight, tonnage = item
        subtotal += weight
        sheet.cell(row=excel_row, column=14, value=seq)
        sheet.cell(row=excel_row, column=15, value=code)
        sheet.cell(row=excel_row, column=16, value=die_sets)
        sheet.cell(row=excel_row, column=17, value=die_number)
        sheet.cell(row=excel_row, column=18, value=length)
        sheet.cell(row=excel_row, column=19, value=width)
        sheet.cell(row=excel_row, column=20, value=height)
        sheet.cell(row=excel_row, column=21, value=hollow)
        sheet.cell(row=excel_row, column=22, value=weight)
        sheet.cell(row=excel_row, column=24, value=tonnage)
    sheet.cell(row=start_row, column=23, value=round(subtotal, 4))
    return end_row


def _write_alloc_notes(sheet: Worksheet, data_end_row: int) -> int:
    """表下方说明：共模 / 一出二比例与模具费计算依据。整行合并，避免写入零件号列。"""
    start_row = data_end_row + 2
    last_row = start_row
    for offset, line in enumerate(_ALLOC_NOTES):
        excel_row = start_row + offset
        sheet.merge_cells(
            start_row=excel_row,
            start_column=1,
            end_row=excel_row,
            end_column=COL_COUNT,
        )
        cell = sheet.cell(row=excel_row, column=1, value=line)
        cell.font = _NOTE_TITLE_FONT if offset == 0 else _NOTE_FONT
        cell.alignment = _LEFT
        sheet.row_dimensions[excel_row].height = 22
        last_row = excel_row
    return last_row


def _apply_layout(sheet: Worksheet, last_row: int) -> None:
    for idx, width in enumerate(_WIDTHS, start=1):
        sheet.column_dimensions[get_column_letter(idx)].width = width
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.print_title_rows = "1:5"
    sheet.print_area = f"A1:{get_column_letter(COL_COUNT)}{last_row}"
    sheet.sheet_view.zoomScale = 90
