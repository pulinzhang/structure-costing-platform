"""年度零件价导入模板 Excel 排版（不含业务查询）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.parsers.bom.annual_part_price_parser import (
    HEADER_PART_NAME,
    HEADER_PART_NUMBER,
    HEADER_REMARK,
    HEADER_SUPPLIER,
    HEADER_SUPPLY_TYPE,
    HEADER_UNIT,
    HEADER_UNIT_PRICE,
)

_SHEET_TITLE = "年度零件价"
_HEADERS = (
    HEADER_PART_NUMBER,
    HEADER_PART_NAME,
    HEADER_UNIT,
    HEADER_UNIT_PRICE,
    HEADER_SUPPLY_TYPE,
    HEADER_SUPPLIER,
    HEADER_REMARK,
)
_COLUMN_WIDTHS = (18, 24, 8, 12, 12, 16, 20)
_UNIT_PRICE_COL = 4
_CENTER_COLS = frozenset({3, 5})


@dataclass(frozen=True)
class AnnualPartPriceTemplateRow:
    """导入模板一行（与解析表头列顺序一致）。"""

    part_number: str
    part_name: str
    unit: str
    unit_price: Decimal
    supply_type: str
    supplier_name: str = ""
    remark: str = ""


def render_import_template(rows: list[AnnualPartPriceTemplateRow]) -> bytes:
    """按解析器约定列写出导入模板工作簿。"""
    workbook = Workbook()
    sheet = workbook.worksheets[0]
    sheet.title = _SHEET_TITLE

    header_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    data_font = Font(name="微软雅黑", size=9)
    align_left = Alignment(horizontal="left", vertical="center")
    align_center = Alignment(horizontal="center", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="BFBFBF"),
        right=Side(style="thin", color="BFBFBF"),
        top=Side(style="thin", color="BFBFBF"),
        bottom=Side(style="thin", color="BFBFBF"),
    )

    for col, title in enumerate(_HEADERS, start=1):
        cell = sheet.cell(row=1, column=col, value=title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    for row_idx, sample in enumerate(rows, start=2):
        values: list[str | Decimal] = [
            sample.part_number,
            sample.part_name,
            sample.unit,
            sample.unit_price,
            sample.supply_type,
            sample.supplier_name,
            sample.remark,
        ]
        for col, value in enumerate(values, start=1):
            cell = sheet.cell(row=row_idx, column=col, value=value)
            cell.font = data_font
            cell.border = thin_border
            if col == _UNIT_PRICE_COL:
                cell.alignment = align_right
                cell.number_format = "0.0000"
            elif col in _CENTER_COLS:
                cell.alignment = align_center
            else:
                cell.alignment = align_left

    for idx, width in enumerate(_COLUMN_WIDTHS, start=1):
        sheet.column_dimensions[get_column_letter(idx)].width = width
    sheet.freeze_panes = "A2"

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
