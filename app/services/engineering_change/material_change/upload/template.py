"""材料变更导入模板：与样表同形、无数据行。"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.engineering_change.material_change.codes import HEADERS, SHEET_HELP, SHEET_ORDER

TEMPLATE_FILENAME = "材料变更导入模板.xlsx"

_THIN = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)
_HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
_HEADER_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
_TITLE_FONT = Font(name="微软雅黑", size=14, bold=True, color="1F4E79")
_HELP_FONT = Font(name="微软雅黑", size=10)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_WIDTHS = (10, 10, 14, 14, 36, 16, 22, 14, 12, 14, 12, 16)
_HELP_LINES = (
    "材料变更填写说明（格子即规格）",
    "",
    "只准两张表：本表 +「工程变更单（材质）」。说明表只认表名。",
    "第 1 行必须是规定的十二列表头。除料厚外，格子必须是文字。禁止合并、公式、贴图。",
    "变更前料厚、变更后料厚必须是数字，大于 0，最多两位小数，例如 1.5。不要写成文字。",
    "变更版本 MAT- 加六位数字，且等于生效年月。生效年月可以写成 2026年6月 或 2026年06月，也可以直接选日期。",
    "互换性只准「不影响互换性」。变更前必须等于库里最新材料。",
)


def build_material_change_template() -> tuple[bytes, str]:
    workbook = Workbook()
    help_sheet = workbook.active
    assert help_sheet is not None
    help_sheet.title = SHEET_HELP
    _write_help(help_sheet)
    _write_order(workbook.create_sheet(SHEET_ORDER))
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue(), TEMPLATE_FILENAME


def _write_help(sheet: Worksheet) -> None:
    sheet.sheet_view.showGridLines = False
    sheet["A1"] = _HELP_LINES[0]
    sheet["A1"].font = _TITLE_FONT
    for index, line in enumerate(_HELP_LINES[1:], start=2):
        sheet.cell(index, 1, line).font = _HELP_FONT
        sheet.cell(index, 1).alignment = _LEFT
    sheet.column_dimensions["A"].width = 110


def _write_order(sheet: Worksheet) -> None:
    for col, title in enumerate(HEADERS, start=1):
        cell = sheet.cell(1, col, title)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _CENTER
        cell.border = _THIN
        if col in (9, 11):
            sheet.column_dimensions[get_column_letter(col)].number_format = "0.00"
        else:
            cell.number_format = "@"
        sheet.column_dimensions[get_column_letter(col)].width = _WIDTHS[col - 1]
    sheet.row_dimensions[1].height = 24
    sheet.freeze_panes = "A2"
