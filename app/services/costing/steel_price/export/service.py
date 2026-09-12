"""钢材联动价导出编排：取数 → 渲染 → 水印文件名。"""

from __future__ import annotations

import logging

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.excel_workbook import resolve_worksheet
from app.common.export_filters import require_at_least_one_export_filter
from app.common.export_watermark import workbook_to_xlsx_bytes
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.schemas.vo.user_vo import UserVO
from app.services.costing.steel_price.export.styles import build_sheet_style
from app.services.costing.steel_price.export.values import build_filename, filter_text
from app.services.costing.steel_price.export.workbook import fill_sheet

logger = logging.getLogger("service.steel_price_export")


class SteelPriceExportService:
    """钢材联动价格 Excel 导出（核对风排版 + 完整溯源）。"""

    def __init__(self) -> None:
        self.repository = SteelPriceRepository()
        self._style = build_sheet_style()

    def export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
        audit_status: str | None = None,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        """
        生成钢材联动价格 Excel。

        溯源列完整导出（基价 / 厚度 / 宽度 / 锌层：ID + 文件名 + 表页 + 行号 + 列号），
        供对账扯皮核对原始 Excel 单元格。

        Returns:
            (文件字节, 文件名)
        """
        require_at_least_one_export_filter(
            year, month, location, category_name, grade, steel_mill, audit_status
        )
        wb = Workbook()
        _title, record_count = self.write_to_workbook(
            wb,
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )
        filename = build_filename(
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )
        content = workbook_to_xlsx_bytes(wb, current_user)
        logger.info(
            "导出钢材联动价格 Excel 完成: filename=%s records=%d",
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
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
        audit_status: str | None = None,
        sheet_title: str = "钢材联动价",
    ) -> tuple[str, int]:
        records = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )
        summary = filter_text(
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )
        ws = resolve_worksheet(wb, sheet_title)
        fill_sheet(ws, records, style=self._style, filter_text=summary)
        return ws.title, len(records)
