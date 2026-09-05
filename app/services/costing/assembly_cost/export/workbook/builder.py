"""把筛选结果写入工作簿各 Sheet（不负责 HTTP / 文件名）。"""

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.excel_workbook import resolve_worksheet
from app.models.costing.assembly_cost import AssemblyCost
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.costing.assembly_cost.assembly_cost_repository import (
    AssemblyCostRepository,
)
from app.services.costing.assembly_cost.export.workbook.codes import collect_welding_fee_ids
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
        list_ws = resolve_worksheet(wb, list_sheet_title)
        write_list_sheet(
            self.layout,
            list_ws,
            records,
            filter_text=filter_text,
            view=view,
            confirm_map=confirm_map,
        )
        write_items_sheet(
            self.layout,
            resolve_worksheet(wb, items_sheet_title),
            records,
            filter_text=filter_text,
            view=view,
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
    from app.services.bom.welding_fee.export_service import BomWeldingFeeExportService

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
