"""成本一览 / 成品核价一览。"""

from typing import Any

from app.common.audit import audit_status_label
from app.models.costing.assembly_cost import AssemblyCost
from app.services.costing.assembly_cost.codes import part_short_code
from app.services.costing.assembly_cost.export.workbook.columns import (
    FINANCE_LIST_SHEET,
    LIST_CENTER_COLS,
    LIST_HEADERS,
    LIST_KPI_COL,
    LIST_MONEY_COLS,
    LIST_WIDTHS,
    PROCUREMENT_LIST_CENTER_COLS,
    PROCUREMENT_LIST_HEADERS,
    PROCUREMENT_LIST_KPI_COL,
    PROCUREMENT_LIST_MONEY_COLS,
    PROCUREMENT_LIST_SHEET,
    PROCUREMENT_LIST_WIDTHS,
)
from app.services.costing.assembly_cost.export.workbook.labels import (
    calc_status_label,
    confirm_status_label,
    object_kind_label,
    tree_level_label,
)
from app.services.costing.assembly_cost.export.workbook.layout import (
    SheetLayout,
    apply_freeze_and_filter,
)
from app.services.costing.assembly_cost.export.workbook.styles import (
    money_cell,
    money_cell_blank_zero,
)


def write_list_sheet(
    layout: SheetLayout,
    ws: Any,
    records: list[AssemblyCost],
    *,
    filter_text: str,
    view: str,
    confirm_map: dict[int, str],
) -> None:
    is_procurement = view == "procurement"
    headers = PROCUREMENT_LIST_HEADERS if is_procurement else LIST_HEADERS
    widths = PROCUREMENT_LIST_WIDTHS if is_procurement else LIST_WIDTHS
    money_cols = PROCUREMENT_LIST_MONEY_COLS if is_procurement else LIST_MONEY_COLS
    kpi_col = PROCUREMENT_LIST_KPI_COL if is_procurement else LIST_KPI_COL
    center_cols = PROCUREMENT_LIST_CENTER_COLS if is_procurement else LIST_CENTER_COLS
    ws.title = PROCUREMENT_LIST_SHEET if is_procurement else FINANCE_LIST_SHEET
    col_count = len(headers)
    header_row = layout.write_banner(
        ws,
        title="零件成本" if is_procurement else "成品核价一览表",
        filter_text=filter_text,
        count_label=f"共 {len(records)} 条",
        note=(
            "说明：本表为核算参考，不参与采购询价/合同业务。"
            "金额列为材料成本、焊接费/电泳黑漆等、总成本（关注列）。"
            "焊接费/电泳黑漆等仅展示名，数据仍为焊接费用。"
            if is_procurement
            else (
                "说明：金额为系统核价快照（材料 / 焊接 / 月总账 / 间接 / 总费用）；"
                "明细 Sheet 仅作佐证，不以 Excel 公式回算。"
            )
        ),
        col_count=col_count,
    )
    layout.write_simple_header(
        ws,
        header_row,
        headers,
        money_cols=money_cols,
        kpi_col=kpi_col,
        header_height=32 if is_procurement else 22,
    )

    for seq, record in enumerate(records, start=1):
        row_idx = header_row + seq
        if is_procurement:
            confirm_status = ""
            if record.procurement_object_id is not None:
                raw = confirm_map.get(int(record.procurement_object_id))
                confirm_status = confirm_status_label(raw)
            row_data = [
                seq,
                part_short_code(part_number=record.part_number, level=record.level),
                record.part_number or "",
                record.part_name or "",
                object_kind_label(record.object_kind),
                tree_level_label(record.level),
                money_cell(record.material_amount),
                money_cell_blank_zero(record.welding_amount),
                money_cell(record.total_amount),
                confirm_status,
                calc_status_label(record.calc_status),
                audit_status_label(record.audit_status),
            ]
        else:
            row_data = [
                seq,
                record.year,
                record.month,
                record.location or "",
                record.part_number or "",
                part_short_code(part_number=record.part_number, level=record.level),
                record.part_name or "",
                record.vehicle_model or "",
                record.bom_version or "",
                money_cell(record.material_amount),
                money_cell(record.welding_amount),
                money_cell(record.total_amount),
                money_cell(record.indirect_amount),
                money_cell(record.grand_total),
                calc_status_label(record.calc_status),
                audit_status_label(record.audit_status),
            ]
        layout.append_styled_row(
            ws,
            row_idx,
            row_data,
            money_cols=money_cols,
            seq=seq,
            center_cols=center_cols,
            kpi_col=kpi_col,
        )

    layout.apply_column_widths(ws, widths)
    apply_freeze_and_filter(
        ws,
        header_row=header_row,
        col_count=col_count,
        row_count=len(records),
    )
    if is_procurement:
        layout.polish_sheet(ws, header_row=header_row)
