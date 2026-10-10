"""成品间接费用 Sheet。"""

from openpyxl.worksheet.worksheet import Worksheet

from app.common.excel_workbook import ExcelCellValue
from app.models.costing.assembly_cost import AssemblyCost
from app.services.costing.assembly_cost.codes import part_short_code
from app.services.costing.assembly_cost.export.workbook.columns import (
    INDIRECT_HEADERS,
    INDIRECT_MONEY_COLS,
    INDIRECT_WIDTHS,
)
from app.services.costing.assembly_cost.export.workbook.layout import SheetLayout
from app.services.costing.assembly_cost.export.workbook.styles import money_cell


def write_indirects_sheet(
    layout: SheetLayout,
    ws: Worksheet,
    records: list[AssemblyCost],
    *,
    filter_text: str,
) -> None:
    header_row = layout.write_banner(
        ws,
        title="成品核价 · 间接费用",
        filter_text=filter_text,
        count_label=f"共 {len(records)} 个成品",
        note="说明：I1～I8 一一列出；费率类以月总账为基数（系统快照）。",
        col_count=len(INDIRECT_HEADERS),
    )
    layout.write_simple_header(
        ws,
        header_row,
        INDIRECT_HEADERS,
        money_cols=INDIRECT_MONEY_COLS,
    )

    row_idx = header_row + 1
    seq = 0
    for record in records:
        for ind in record.indirects or []:
            seq += 1
            row_data: list[ExcelCellValue] = [
                seq,
                record.year,
                record.month,
                record.location or "",
                record.vehicle_model or "",
                record.bom_version or "",
                record.part_number or "",
                part_short_code(part_number=record.part_number, level=record.level),
                ind.code or "",
                ind.label or "",
                money_cell(ind.amount),
                money_cell(ind.rate) if ind.rate is not None else "",
                money_cell(ind.base_amount) if ind.base_amount is not None else "",
            ]
            layout.append_styled_row(
                ws,
                row_idx,
                row_data,
                money_cols=INDIRECT_MONEY_COLS,
                seq=seq,
            )
            row_idx += 1

    layout.apply_column_widths(ws, INDIRECT_WIDTHS)
    ws.freeze_panes = f"A{header_row + 1}"
