"""采购对象列表导出编排：取数 → 分 sheet 渲染 → 水印文件名。"""

from __future__ import annotations

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.export_watermark import workbook_to_xlsx_bytes
from app.common.timezone import now
from app.models.bom.procurement_object import BomProcurementObject
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.dto.bom_procurement_object_dto import BomProcurementObjectQuery
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.mapping import (
    as_of_when_excluding_expired,
    load_l0_period_map,
    scope_from_query,
)
from app.services.bom.procurement_object.styles import SHEETS
from app.services.bom.procurement_object.values import build_filename
from app.services.bom.procurement_object.workbook import write_data_sheet
from app.services.masterdata.supplier.service import SupplierService


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
        as_of_year, as_of_month = as_of_when_excluding_expired(query.include_expired)
        if supplier_names is not None and not supplier_names:
            rows: list[BomProcurementObject] = []
        else:
            rows = self.repository.list_objects_for_export(
                db,
                scope=scope_from_query(
                    query,
                    location=query.location,
                    supplier_names=supplier_names,
                    as_of_year=as_of_year,
                    as_of_month=as_of_month,
                ),
            )
        period_map = load_l0_period_map(db, self.repository, rows)
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
            write_data_sheet(sheet, sheet_rows, query, stamp, title, period_map=period_map)

        content = workbook_to_xlsx_bytes(workbook, current_user)
        filename = build_filename(query, stamp)
        return content, filename
