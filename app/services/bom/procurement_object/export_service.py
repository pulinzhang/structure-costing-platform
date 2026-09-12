"""采购对象清单导出编排：取数 → 分 sheet 渲染 → 水印文件名。"""

from __future__ import annotations

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.export_watermark import workbook_to_xlsx_bytes
from app.common.timezone import now
from app.models.bom.procurement_object import BomProcurementObject
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.dto.bom_procurement_object_dto import BomProcurementObjectQuery
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.styles import SHEETS
from app.services.bom.procurement_object.values import build_filename
from app.services.bom.procurement_object.workbook import write_data_sheet
from app.services.masterdata.supplier import SupplierService


class BomProcurementObjectExportService:
    def __init__(self) -> None:
        self.repository = BomProcurementObjectRepository()

    def export_excel(
        self,
        db: Session,
        query: BomProcurementObjectQuery,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        supplier_names = SupplierService().names_for_query(db, query.supplier_name)
        if supplier_names is not None and not supplier_names:
            rows: list[BomProcurementObject] = []
        else:
            rows = self.repository.list_objects_for_export(
                db,
                location=query.location,
                vehicle_model=query.vehicle_model,
                bom_version=query.bom_version,
                section=query.section,
                object_kind=query.object_kind,
                confirm_status=query.confirm_status,
                audit_status=query.audit_status,
                part_number=query.part_number,
                l0_part_number=query.l0_part_number,
                excel_row=query.excel_row,
                supplier_names=supplier_names,
                has_supplier=query.has_supplier,
            )
        stamp = now()
        workbook = Workbook()
        first_sheet = True
        for title, section, tab_color in SHEETS:
            if query.section and query.section != section:
                continue
            sheet_rows = [row for row in rows if row.section == section]
            if first_sheet:
                sheet = workbook.worksheets[0]
                sheet.title = title
                first_sheet = False
            else:
                sheet = workbook.create_sheet(title)
            sheet.sheet_properties.tabColor = tab_color
            write_data_sheet(sheet, sheet_rows, query, stamp, title)

        content = workbook_to_xlsx_bytes(workbook, current_user)
        filename = build_filename(query, stamp)
        return content, filename
