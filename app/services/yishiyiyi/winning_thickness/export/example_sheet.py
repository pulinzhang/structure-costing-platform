"""中标厚度价格一览 Excel — 使用示例页。"""

from __future__ import annotations

from decimal import Decimal

from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.common.money import Q2, excel_money_cell
from app.schemas.vo.winning_thickness_vo import WinningThicknessRowVO
from app.services.yishiyiyi.winning_thickness.export.letterhead import (
    WorkbookMeta,
    apply_sheet_chrome,
    write_letterhead,
)
from app.services.yishiyiyi.winning_thickness.export.styles import (
    DATA_FONT,
    DATA_LEFT,
    DATA_RIGHT,
    FINAL_COL_FILL,
    FINAL_FONT,
    FINAL_HEADER_FILL,
    HEADER_ALIGNMENT,
    HEADER_FILL,
    HEADER_FONT,
    INPUT_FILL,
    MUTED_FONT,
    NOTE_FILL,
    NOTE_FONT,
    PRICE_FORMAT,
    SECTION_FONT,
    THICK_FORMAT,
    THIN_BORDER,
    WRAP_TOP,
    zebra_fill,
)
from app.services.yishiyiyi.winning_thickness.export.values import (
    CALC_SHEET_SUFFIX,
    EXAMPLE_TAB_COLOR,
    TABLE_HEADER_ROW,
    excel_sheet_ref,
    pick_example_rows,
    sample_thickness,
    scoped_sheet_name,
)

_HEADERS = [
    "基地",
    "钢种",
    "牌号",
    "钢厂",
    "厚度",
    "基准价(元/吨)",
    "加减价(元/吨)",
    "加工费(元/吨)",
    "最终价(元/吨)",
]
_COLUMN_WIDTHS = [14, 14, 14, 12, 12, 16, 16, 16, 16]
_THICK_COL = 5
_PRICE_COLS = frozenset({6, 7, 8, 9})
_FINAL_COL = 9
_LETTERHEAD_COLS = 10


def write_example_sheet(
    ws: Worksheet,
    rows: list[WinningThicknessRowVO],
    meta: WorkbookMeta,
) -> None:
    examples = pick_example_rows(rows)
    header_row = write_letterhead(
        ws,
        last_col=_LETTERHEAD_COLS,
        meta=meta,
        sheet_role="使用示例 · 改黄色格料厚即可套价",
        formula_note=(
            "黄色格填写厚度；基准价、加减价、加工费从「计算用」页按"
            "基地、牌号和厚度区间自动带出（不按钢厂筛选），最终价 = 三者之和。"
        ),
    )
    _write_header(ws, header_row)
    calc_start = TABLE_HEADER_ROW + 1
    calc_end = TABLE_HEADER_ROW + max(len(rows), 1)
    calc_sheet_name = scoped_sheet_name(
        year=meta.year,
        month=meta.month,
        location=meta.location,
        suffix=CALC_SHEET_SUFFIX,
    )
    data_start = header_row + 1
    if examples:
        for offset, row in enumerate(examples):
            _write_data_row(
                ws,
                data_start + offset,
                offset,
                row,
                calc_start=calc_start,
                calc_end=calc_end,
                calc_sheet_name=calc_sheet_name,
            )
        last_data_row = data_start + len(examples) - 1
    else:
        _write_data_row(
            ws,
            data_start,
            0,
            None,
            calc_start=calc_start,
            calc_end=calc_end,
            calc_sheet_name=calc_sheet_name,
        )
        last_data_row = data_start
        empty = ws.cell(row=data_start + 1, column=1, value="本次无数据可摘录。")
        empty.font = MUTED_FONT

    for col_idx, width in enumerate(_COLUMN_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    _write_formula_notes(ws, start_row=last_data_row + 2, data_start=data_start)
    apply_sheet_chrome(
        ws,
        last_col=_LETTERHEAD_COLS,
        header_row=header_row,
        meta=meta,
        tab_color=EXAMPLE_TAB_COLOR,
        freeze=False,
    )


def _write_header(ws: Worksheet, header_row: int) -> None:
    for col_idx, title in enumerate(_HEADERS, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=title)
        cell.font = HEADER_FONT
        cell.fill = FINAL_HEADER_FILL if col_idx == _FINAL_COL else HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER
    ws.row_dimensions[header_row].height = 28


def _write_data_row(
    ws: Worksheet,
    excel_row: int,
    data_index: int,
    row: WinningThicknessRowVO | None,
    *,
    calc_start: int,
    calc_end: int,
    calc_sheet_name: str,
) -> None:
    thickness: Decimal | None = sample_thickness(row) if row is not None else None
    values: list[Decimal | str | None] = [
        (row.location or "") if row is not None else "",
        (row.category_name or "") if row is not None else "",
        (row.grade or "") if row is not None else "",
        (row.steel_mill or "") if row is not None else "",
        excel_money_cell(thickness, Q2) if thickness is not None else None,
        _lookup_formula(excel_row, calc_start, calc_end, "I", calc_sheet_name),
        _lookup_formula(excel_row, calc_start, calc_end, "J", calc_sheet_name),
        _lookup_formula(excel_row, calc_start, calc_end, "K", calc_sheet_name),
        f'=IF(F{excel_row}="","",F{excel_row}+G{excel_row}+H{excel_row})',
    ]
    stripe = zebra_fill(data_index)
    for col_idx, value in enumerate(values, start=1):
        cell = ws.cell(row=excel_row, column=col_idx, value=value)
        cell.border = THIN_BORDER
        cell.font = FINAL_FONT if col_idx == _FINAL_COL else DATA_FONT
        if col_idx == _THICK_COL:
            cell.fill = INPUT_FILL
            cell.alignment = DATA_RIGHT
            cell.number_format = THICK_FORMAT
        elif col_idx in _PRICE_COLS:
            cell.fill = FINAL_COL_FILL if col_idx == _FINAL_COL else stripe
            cell.alignment = DATA_RIGHT
            cell.number_format = PRICE_FORMAT
        else:
            cell.fill = stripe
            cell.alignment = DATA_LEFT


def _lookup_match_expr(
    excel_row: int,
    start: int,
    end: int,
    calc_sheet_name: str,
) -> str:
    sheet = excel_sheet_ref(calc_sheet_name)
    thickness = f"$E{excel_row}"
    loc = f"{sheet}!$A${start}:$A${end}"
    grade = f"{sheet}!$C${start}:$C${end}"
    thick_min = f"{sheet}!$E${start}:$E${end}"
    min_op = f"{sheet}!$F${start}:$F${end}"
    thick_max = f"{sheet}!$G${start}:$G${end}"
    max_op = f"{sheet}!$H${start}:$H${end}"
    keys = f"({loc}=$A{excel_row})*({grade}=$C{excel_row})"
    min_ok = (
        f'((({thick_min}="")+({min_op}=">=")*({thickness}>={thick_min})'
        f'+({min_op}=">")*({thickness}>{thick_min})'
        f'+({min_op}="")*({thick_min}<>"")*({thickness}>={thick_min}))>0)'
    )
    max_ok = (
        f'((({thick_max}="")+({max_op}="<=")*({thickness}<={thick_max})'
        f'+({max_op}="<")*({thickness}<{thick_max})'
        f'+({max_op}="")*({thick_max}<>"")*({thickness}<={thick_max}))>0)'
    )
    return f"{keys}*{min_ok}*{max_ok}"


def _lookup_formula(
    excel_row: int,
    start: int,
    end: int,
    value_col: str,
    calc_sheet_name: str,
) -> str:
    match = _lookup_match_expr(excel_row, start, end, calc_sheet_name)
    sheet = excel_sheet_ref(calc_sheet_name)
    values = f"{sheet}!${value_col}${start}:${value_col}${end}"
    return (
        f'=IF($E{excel_row}="","",'
        f'IF(SUMPRODUCT({match})=0,"",'
        f"SUMPRODUCT({match}*({values}))))"
    )


def _write_formula_notes(ws: Worksheet, *, start_row: int, data_start: int) -> None:
    heading = ws.cell(row=start_row, column=1, value="公式说明")
    heading.font = SECTION_FONT
    last_col = len(_HEADERS)
    ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=last_col)
    notes = [
        "黄色格填写厚度，可改。基地、牌号也可改成要查的规格。",
        "基准价、加减价、加工费：按「计算用」页匹配基地、牌号，"
        "且厚度落在上下限内（空上下限表示不限制）。不按钢厂筛选。",
        "最终价 = 基准价 + 厚度加减价 + 加工费。",
        f'第 {data_start} 行最终价公式：=IF(F{data_start}="","",F{data_start}+G{data_start}+H{data_start})',
    ]
    for offset, text in enumerate(notes, start=1):
        excel_row = start_row + offset
        ws.merge_cells(
            start_row=excel_row,
            start_column=1,
            end_row=excel_row,
            end_column=last_col,
        )
        cell = ws.cell(row=excel_row, column=1, value=text)
        cell.font = NOTE_FONT
        cell.alignment = WRAP_TOP
        cell.fill = NOTE_FILL
        ws.row_dimensions[excel_row].height = 20
