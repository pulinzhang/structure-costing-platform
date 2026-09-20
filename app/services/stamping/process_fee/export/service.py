"""冲压加工费导出编排：取数 → 渲染 → 水印文件名。"""

from __future__ import annotations

import logging

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.excel_workbook import resolve_worksheet
from app.common.export_filters import require_at_least_one_export_filter
from app.common.export_watermark import workbook_to_xlsx_bytes
from app.repositories.stamping.process_fee.repository import (
    StampingProcessFeeRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.supplier.supplier_service import SupplierService
from app.services.stamping.process_fee.export.styles import build_sheet_style
from app.services.stamping.process_fee.export.values import build_filename, filter_text
from app.services.stamping.process_fee.export.workbook import fill_sheet

logger = logging.getLogger("service.stamping_process_fee_export")


class StampingProcessFeeExportService:
    """冲压加工费 Excel 导出（主表合并 + 工序明细分行）。"""

    def __init__(self) -> None:
        self.repository = StampingProcessFeeRepository()
        self._style = build_sheet_style()

    def export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        require_at_least_one_export_filter(
            year,
            location,
            stamping_supplier,
            vehicle_model,
            version,
            part_number,
            audit_status,
        )
        wb = Workbook()
        _title, fee_count = self.write_to_workbook(
            wb,
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )

        content = workbook_to_xlsx_bytes(wb, current_user)
        filename = build_filename(
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
        )
        logger.info("导出冲压加工费 %s 条主表 -> %s", fee_count, filename)
        return content, filename

    def write_to_workbook(
        self,
        wb: Workbook,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        sheet_title: str = "冲压加工费",
    ) -> tuple[str, int]:
        records = self.repository.list_for_export(
            db,
            year=year,
            location=location,
            stamping_suppliers=SupplierService().names_for_query(db, stamping_supplier),
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )

        ws = resolve_worksheet(wb, sheet_title)
        summary = filter_text(
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        export_row_count = fill_sheet(
            ws,
            records,
            style=self._style,
            filter_text=summary,
        )
        logger.info(
            "写入冲压加工费 sheet=%s 主表=%s 明细行=%s",
            ws.title,
            len(records),
            export_row_count,
        )
        return ws.title, len(records)
