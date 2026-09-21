"""把筛选结果写入工作簿各 Sheet（不负责 HTTP / 文件名）。"""

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.excel_workbook import resolve_worksheet
from app.models.bom.node import BomNode
from app.models.costing.assembly_cost import AssemblyCost
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.costing.assembly_cost.assembly_cost_repository import (
    AssemblyCostRepository,
)
from app.repositories.costing.assembly_cost.payloads import _chunks
from app.services.costing.assembly_cost.export.workbook.columns import (
    FINANCE_INDIRECTS_SHEET,
    FINANCE_ITEMS_SHEET,
    FINANCE_LIST_SHEET,
    FINANCE_WELDING_SHEET,
    PROCUREMENT_ITEMS_SHEET,
    PROCUREMENT_LIST_SHEET,
    PROCUREMENT_WELDING_SHEET,
)
from app.services.costing.assembly_cost.export.workbook.indirects_sheet import (
    write_indirects_sheet,
)
from app.services.costing.assembly_cost.export.workbook.items_sheet import write_items_sheet
from app.services.costing.assembly_cost.export.workbook.labels import export_filter_text
from app.services.costing.assembly_cost.export.workbook.layout import SheetLayout
from app.services.costing.assembly_cost.export.workbook.list_sheet import write_list_sheet
from app.services.costing.assembly_cost.export.workbook.missing_l0_seq import (
    find_missing_l0_seqs,
    format_missing_l0_seq_note,
)


def collect_welding_fee_ids(records: list[AssemblyCost]) -> list[int]:
    """导出卡实际抄到的焊费行，去重保序。"""
    seen: dict[int, None] = {}
    for record in records:
        fee_id = record.welding_fee_id
        if fee_id is None:
            continue
        seen[int(fee_id)] = None
    return list(seen)


class AssemblyCostWorkbookBuilder:
    def __init__(self) -> None:
        self.repository = AssemblyCostRepository()
        self.layout = SheetLayout()

    def write(
        self,
        wb: Workbook,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        view: str = "finance",
        list_sheet_title: str | None = None,
        items_sheet_title: str | None = None,
        indirects_sheet_title: str = FINANCE_INDIRECTS_SHEET,
        welding_sheet_title: str | None = None,
    ) -> tuple[str, int]:
        is_procurement = view == "procurement"
        if list_sheet_title is None:
            list_sheet_title = PROCUREMENT_LIST_SHEET if is_procurement else FINANCE_LIST_SHEET
        if items_sheet_title is None:
            items_sheet_title = PROCUREMENT_ITEMS_SHEET if is_procurement else FINANCE_ITEMS_SHEET
        if welding_sheet_title is None:
            welding_sheet_title = (
                PROCUREMENT_WELDING_SHEET if is_procurement else FINANCE_WELDING_SHEET
            )
        records = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            view=view,
        )
        filter_text = export_filter_text(
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            view=view,
        )
        confirm_map = _confirm_map_for_view(db, view, records)
        seq_no_map = {} if is_procurement else _seq_no_by_source_node_id(db, records)
        missing_l0_note = ""
        if not is_procurement:
            missing_rows, universe_max = find_missing_l0_seqs(
                db,
                records,
                year=year,
                month=month,
                location=location,
                vehicle_model=vehicle_model,
                part_number=part_number,
                audit_status=audit_status,
                calc_status=calc_status,
                export_seq_nos=seq_no_map,
            )
            missing_l0_note = format_missing_l0_seq_note(
                missing_rows,
                export_count=len(records),
                universe_max_seq=universe_max,
            )
        list_ws = resolve_worksheet(wb, list_sheet_title)
        write_list_sheet(
            self.layout,
            list_ws,
            records,
            filter_text=filter_text,
            view=view,
            confirm_map=confirm_map,
            seq_no_by_source_node_id=seq_no_map,
            missing_l0_note=missing_l0_note,
        )
        write_items_sheet(
            self.layout,
            resolve_worksheet(wb, items_sheet_title),
            records,
            filter_text=filter_text,
            view=view,
            seq_no_by_source_node_id=seq_no_map,
        )
        _write_welding_sheet(
            wb,
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            records=records,
            sheet_title=welding_sheet_title,
            omit_scope_columns=is_procurement,
        )
        if not is_procurement:
            write_indirects_sheet(
                self.layout,
                resolve_worksheet(wb, indirects_sheet_title),
                records,
                filter_text=filter_text,
            )
        return list_ws.title, len(records)


def _seq_no_by_source_node_id(
    db: Session,
    records: list[AssemblyCost],
) -> dict[int, int | None]:
    """财务树根 source_node_id = L0；导出序号列直接用节点 seq_no。"""
    node_ids = sorted(
        {
            int(source_node_id)
            for record in records
            if (source_node_id := getattr(record, "source_node_id", None)) is not None
        }
    )
    if not node_ids:
        return {}
    result: dict[int, int | None] = {}
    for chunk in _chunks(node_ids):
        rows = db.query(BomNode.id, BomNode.seq_no).filter(BomNode.id.in_(chunk)).all()
        for node_id, seq_no in rows:
            result[int(node_id)] = int(seq_no) if seq_no is not None else None
    return result


def _confirm_map_for_view(
    db: Session,
    view: str,
    records: list[AssemblyCost],
) -> dict[int, str]:
    if view != "procurement":
        return {}
    object_ids = [
        int(record.procurement_object_id)
        for record in records
        if record.procurement_object_id is not None
    ]
    return BomProcurementObjectRepository().map_confirm_status_by_ids(db, object_ids)


def _write_welding_sheet(
    wb: Workbook,
    db: Session,
    *,
    year: int | None,
    location: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    records: list[AssemblyCost],
    sheet_title: str,
    omit_scope_columns: bool,
) -> None:
    from app.services.bom.welding_fee.export.service import BomWeldingFeeExportService

    BomWeldingFeeExportService().write_to_workbook(
        wb,
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        ids=collect_welding_fee_ids(records),
        sheet_title=sheet_title,
        omit_scope_columns=omit_scope_columns,
    )
