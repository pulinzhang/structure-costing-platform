"""冲压模具费导出编排：取数 → 渲染 → 水印文件名。"""

from __future__ import annotations

import logging

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.excel_workbook import resolve_worksheet
from app.common.export_filters import require_at_least_one_export_filter
from app.common.export_watermark import workbook_to_xlsx_bytes
from app.common.vehicle_model import normalize_vehicle_model
from app.models.stamping.die import StampingDieProcess
from app.models.stamping.die_fee import StampingDieFee
from app.repositories.stamping.die.repository import StampingDieProcessRepository
from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.location.location_service import LocationService
from app.services.stamping.die_fee.export.styles import build_sheet_style
from app.services.stamping.die_fee.export.values import build_filename, filter_text
from app.services.stamping.die_fee.export.workbook import fill_sheet

logger = logging.getLogger("service.stamping_die_fee_export")


class StampingDieFeeExportService:
    """冲压模具费 Excel 导出（主表合并 + 各序明细分行）。"""

    def __init__(self) -> None:
        self.fee_repo = StampingDieFeeRepository()
        self.process_repo = StampingDieProcessRepository()
        self._style = build_sheet_style()

    def export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        only_zero: bool = False,
        stamping_supplier: str | None = None,
        version: str | None = None,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        loc = (location or "").strip() or None
        vehicle = normalize_vehicle_model(vehicle_model) if vehicle_model else None
        vehicle = vehicle or None
        part = (part_number or "").strip() or None
        supplier = (stamping_supplier or "").strip() or None
        version_value = (version or "").strip() or None
        status = (audit_status or "").strip() or None

        require_at_least_one_export_filter(
            year,
            loc,
            vehicle,
            supplier,
            version_value,
            part,
            status,
            only_zero,
        )

        locations: list[str] | None = None
        if loc:
            locations = LocationService().expand_for_query(db, loc)
            if not locations:
                locations = []

        workbook = Workbook()
        _title, fee_count = self._write_to_workbook(
            workbook,
            db,
            year=year,
            location=loc,
            locations=locations,
            vehicle_model=vehicle,
            part_number=part,
            audit_status=status,
            only_zero=only_zero,
            stamping_supplier=supplier,
            version=version_value,
        )

        content = workbook_to_xlsx_bytes(workbook, current_user)
        filename = build_filename(
            year=year,
            location=loc,
            vehicle_model=vehicle,
            stamping_supplier=supplier,
            version=version_value,
        )
        logger.info("导出冲压模具费 %s 条主表 -> %s", fee_count, filename)
        return content, filename

    def _write_to_workbook(
        self,
        workbook: Workbook,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
        stamping_supplier: str | None = None,
        version: str | None = None,
        sheet_title: str = "冲压模具费",
    ) -> tuple[str, int]:
        records = self.fee_repo.list_for_export(
            db,
            year=year,
            location=location if locations is None else None,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
            stamping_supplier=stamping_supplier,
            version=version,
        )
        process_by_id = self._load_source_processes(db, records)
        sheet = resolve_worksheet(workbook, sheet_title)
        summary = filter_text(
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            stamping_supplier=stamping_supplier,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
        )
        export_row_count = fill_sheet(
            sheet,
            records,
            style=self._style,
            process_by_id=process_by_id,
            filter_text=summary,
        )
        logger.info(
            "写入冲压模具费 sheet=%s 主表=%s 明细行=%s",
            sheet.title,
            len(records),
            export_row_count,
        )
        return sheet.title, len(records)

    def _load_source_processes(
        self,
        db: Session,
        records: list[StampingDieFee],
    ) -> dict[int, StampingDieProcess]:
        process_ids = [
            item.source_die_process_id
            for record in records
            for item in (record.items or [])
            if item.source_die_process_id
        ]
        processes = self.process_repo.list_by_ids(db, process_ids)
        return {process.id: process for process in processes}
