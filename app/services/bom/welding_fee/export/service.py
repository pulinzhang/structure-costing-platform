"""焊接费导出编排：取数 → 渲染 → 水印文件名。"""

from __future__ import annotations

import logging

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.excel_workbook import resolve_worksheet
from app.common.export_filters import require_at_least_one_export_filter
from app.common.export_watermark import workbook_to_xlsx_bytes
from app.models.bom import BomWeldingFee
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_welding_fee_dto import resolve_welding_fee_levels
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_fee.export.columns import WeldingSheetLayout
from app.services.bom.welding_fee.export.styles import build_sheet_style
from app.services.bom.welding_fee.export.values import build_filename, filter_text
from app.services.bom.welding_fee.export.workbook import fill_sheet

logger = logging.getLogger("service.bom.welding_fee.export")


class BomWeldingFeeExportService:
    """按筛选导出焊接费（主表合并 + 工艺明细分行）。"""

    def __init__(self) -> None:
        self.fee_repo = BomWeldingFeeRepository()
        self.breakdown_repo = BomWeldingProcessBreakdownRepository()
        self._style = build_sheet_style()
        self._layout = WeldingSheetLayout(omit_scope=False)

    def write_to_workbook(
        self,
        wb: Workbook,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
        ids: list[int] | None = None,
        sheet_title: str = "焊接费",
        omit_scope_columns: bool = False,
    ) -> tuple[str, int]:
        self._layout = WeldingSheetLayout(omit_scope=omit_scope_columns)
        resolved_levels = resolve_welding_fee_levels(level=level, levels=levels)
        records = self.fee_repo.list_for_export(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            levels=resolved_levels,
            ids=ids,
        )
        self._fill_missing_weld_info(db, records)

        ws = resolve_worksheet(wb, sheet_title)
        summary = filter_text(
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            levels=resolved_levels,
            ids=ids,
        )
        fill_sheet(
            ws,
            records,
            layout=self._layout,
            style=self._style,
            filter_text=summary,
        )
        return ws.title, len(records)

    def export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        require_at_least_one_export_filter(
            year,
            location,
            vehicle_model,
            bom_version,
            part_number,
            audit_status,
            calc_status,
        )
        wb = Workbook()
        _title, fee_count = self.write_to_workbook(
            wb,
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
            levels=levels,
        )
        # header_row is always 5 (banner 1–3 + group 4 + headers 5); last row is 合计
        export_row_count = max(0, wb.worksheets[0].max_row - 6)

        content = workbook_to_xlsx_bytes(wb, current_user)
        filename = build_filename(
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        logger.info(
            "导出焊接费 %s 条主表 / %s 行明细 / 文件 %s",
            fee_count,
            export_row_count,
            filename,
        )
        return content, filename

    def _fill_missing_weld_info(self, db: Session, records: list[BomWeldingFee]) -> None:
        need_ids = [
            int(r.source_breakdown_node_id)
            for r in records
            if r.source_breakdown_node_id and not (r.weld_info_raw or "").strip()
        ]
        if not need_ids:
            return
        weld_map = self.breakdown_repo.map_weld_info_by_ids(db, need_ids)
        for record in records:
            if (record.weld_info_raw or "").strip():
                continue
            node_id = record.source_breakdown_node_id
            if not node_id:
                continue
            text = weld_map.get(int(node_id))
            if text:
                record.weld_info_raw = text
