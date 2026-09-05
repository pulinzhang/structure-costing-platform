"""材料明细 Sheet。"""

from typing import Any

from app.models.costing.assembly_cost import AssemblyCost
from app.services.costing.assembly_cost.export.workbook.codes import (
    item_short_code,
    part_short_code,
)
from app.services.costing.assembly_cost.export.workbook.columns import (
    FINANCE_ITEM_HEADERS,
    FINANCE_ITEM_MONEY_COLS,
    FINANCE_ITEM_WIDTHS,
    PROCUREMENT_ITEM_CENTER_COLS,
    PROCUREMENT_ITEM_CHILD_FIRST_COL,
    PROCUREMENT_ITEM_GROUP_COLS,
    PROCUREMENT_ITEM_GROUP_LAST_COL,
    PROCUREMENT_ITEM_HEADERS,
    PROCUREMENT_ITEM_MONEY_COLS,
    PROCUREMENT_ITEM_PART_NUMBER_COL,
    PROCUREMENT_ITEM_WIDTHS,
)
from app.services.costing.assembly_cost.export.workbook.labels import (
    cost_source_label,
    match_hint_label,
    tree_level_label,
)
from app.services.costing.assembly_cost.export.workbook.layout import SheetLayout
from app.services.costing.assembly_cost.export.workbook.styles import fill, font, money_cell


def write_items_sheet(
    layout: SheetLayout,
    ws: Any,
    records: list[AssemblyCost],
    *,
    filter_text: str,
    view: str,
) -> None:
    is_procurement = view == "procurement"
    headers = PROCUREMENT_ITEM_HEADERS if is_procurement else FINANCE_ITEM_HEADERS
    money_cols = PROCUREMENT_ITEM_MONEY_COLS if is_procurement else FINANCE_ITEM_MONEY_COLS
    header_row = layout.write_banner(
        ws,
        title="材料明细" if is_procurement else "成品核价 · 材料明细",
        filter_text=filter_text,
        count_label=(
            f"共 {len(records)} 个采购对象" if is_procurement else f"共 {len(records)} 个成品"
        ),
        note=(
            "说明：范围已在表头锁定；同一采购对象身份列纵向合并，子件分行佐证；"
            "子件短码仅冲压零件价，标准件等只列完整零件号；"
            "一口价剪枝行仍列出但不计价；行金额为计算快照。"
            if is_procurement
            else "说明：一口价剪枝行仍列出但不计价；行金额为计算快照。"
        ),
        col_count=len(headers),
    )
    if is_procurement:
        _write_procurement_item_headers(layout, ws, header_row, headers)
        data_start = header_row + 2
    else:
        layout.write_simple_header(ws, header_row, headers, money_cols=money_cols)
        data_start = header_row + 1

    row_idx = data_start
    seq = 0
    object_seq = 0
    for record in records:
        items = list(record.items or [])
        if not items:
            continue
        object_seq += 1
        group_start = row_idx
        for item in items:
            seq += 1
            if is_procurement:
                row_data = [
                    object_seq,
                    part_short_code(part_number=record.part_number, level=record.level),
                    record.part_number or "",
                    record.part_name or "",
                    tree_level_label(item.node_level),
                    item_short_code(
                        part_number=item.part_number,
                        level=item.node_level,
                        cost_source=item.cost_source,
                    ),
                    item.part_number or "",
                    item.part_name or "",
                    cost_source_label(item.cost_source),
                    match_hint_label(item.match_hint),
                    money_cell(item.unit_price),
                    money_cell(item.effective_qty),
                    money_cell(item.line_amount),
                ]
            else:
                row_data = [
                    seq,
                    record.year,
                    record.month,
                    record.location or "",
                    record.vehicle_model or "",
                    record.bom_version or "",
                    record.part_number or "",
                    part_short_code(part_number=record.part_number, level=record.level),
                    tree_level_label(item.node_level),
                    item.part_number or "",
                    item_short_code(
                        part_number=item.part_number,
                        level=item.node_level,
                        cost_source=item.cost_source,
                    ),
                    item.part_name or "",
                    cost_source_label(item.cost_source),
                    match_hint_label(item.match_hint),
                    money_cell(item.unit_price),
                    money_cell(item.effective_qty),
                    money_cell(item.line_amount),
                ]
            layout.append_styled_row(
                ws,
                row_idx,
                row_data,
                money_cols=money_cols,
                seq=object_seq if is_procurement else seq,
                center_cols=PROCUREMENT_ITEM_CENTER_COLS if is_procurement else {1},
            )
            row_idx += 1
        if is_procurement:
            layout.merge_item_group(
                ws,
                start_row=group_start,
                end_row=row_idx - 1,
                columns=PROCUREMENT_ITEM_GROUP_COLS,
                left_cols={PROCUREMENT_ITEM_PART_NUMBER_COL},
            )

    widths = PROCUREMENT_ITEM_WIDTHS if is_procurement else FINANCE_ITEM_WIDTHS
    layout.apply_column_widths(ws, widths)
    ws.freeze_panes = f"A{data_start}"
    if is_procurement:
        layout.polish_sheet(ws, header_row=data_start - 1)


def _write_procurement_item_headers(
    layout: SheetLayout,
    ws: Any,
    header_row: int,
    headers: list[str],
) -> None:
    group_end = PROCUREMENT_ITEM_GROUP_LAST_COL
    child_start = PROCUREMENT_ITEM_CHILD_FIRST_COL
    col_count = len(headers)
    ws.merge_cells(
        start_row=header_row,
        start_column=1,
        end_row=header_row,
        end_column=group_end,
    )
    ws.merge_cells(
        start_row=header_row,
        start_column=child_start,
        end_row=header_row,
        end_column=col_count,
    )
    object_cell = ws.cell(row=header_row, column=1, value="采购对象")
    object_cell.font = font(size=10, bold=True, color="FFFFFF")
    object_cell.fill = fill("546E7A")
    object_cell.alignment = layout.center
    object_cell.border = layout.border
    for col in range(2, group_end + 1):
        cell = ws.cell(row=header_row, column=col)
        cell.fill = fill("546E7A")
        cell.border = layout.border
    child_cell = ws.cell(row=header_row, column=child_start, value="子件构成（佐证）")
    child_cell.font = font(size=10, bold=True, color="FFFFFF")
    child_cell.fill = fill("EF6C00")
    child_cell.alignment = layout.center
    child_cell.border = layout.border
    for col in range(child_start + 1, col_count + 1):
        cell = ws.cell(row=header_row, column=col)
        cell.fill = fill("EF6C00")
        cell.border = layout.border
    ws.row_dimensions[header_row].height = 20
    layout.write_simple_header(
        ws,
        header_row + 1,
        headers,
        money_cols=PROCUREMENT_ITEM_MONEY_COLS,
    )
