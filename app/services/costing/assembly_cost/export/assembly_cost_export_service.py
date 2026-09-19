"""成品月核价 Excel 导出入口：筛选校验、落文件名、水印字节。"""

import logging

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.export_filters import (
    require_at_least_one_export_filter,
    require_period_scope_export_filters,
)
from app.common.export_watermark import workbook_to_xlsx_bytes
from app.schemas.vo.user_vo import UserVO
from app.services.costing.assembly_cost.export.workbook.builder import (
    AssemblyCostWorkbookBuilder,
)
from app.services.costing.assembly_cost.export.workbook.columns import (
    FINANCE_INDIRECTS_SHEET,
    PROCUREMENT_FILE_PREFIX,
)
from app.services.costing.assembly_cost.export.workbook.filename import (
    build_export_filename,
)

logger = logging.getLogger("service.assembly_cost.export")


class AssemblyCostExportService:
    """按当前筛选导出成品核价（列表所见优先，排版对齐核对表）。"""

    def __init__(self) -> None:
        self.builder = AssemblyCostWorkbookBuilder()

    def export(
        self,
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
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        if view == "procurement":
            require_period_scope_export_filters(
                year,
                month,
                location,
                vehicle_model,
                bom_version,
            )
        else:
            require_at_least_one_export_filter(
                year,
                month,
                location,
                vehicle_model,
                bom_version,
                part_number,
                audit_status,
                calc_status,
            )
        wb = Workbook()
        _title, record_count = self.write_to_workbook(
            wb,
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
        filename = build_export_filename(
            view=view,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        content = workbook_to_xlsx_bytes(wb, current_user)
        prefix = PROCUREMENT_FILE_PREFIX if view == "procurement" else "成品核价"
        logger.info(
            "导出%s Excel: filename=%s records=%d",
            prefix,
            filename,
            record_count,
        )
        return content, filename

    def write_to_workbook(
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
        """月度核对导出与单文件导出共用：往已有 Workbook 写 Sheet。"""
        return self.builder.write(
            wb,
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
            list_sheet_title=list_sheet_title,
            items_sheet_title=items_sheet_title,
            indirects_sheet_title=indirects_sheet_title,
            welding_sheet_title=welding_sheet_title,
        )
