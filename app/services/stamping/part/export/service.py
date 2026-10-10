"""冲压零件导出编排：工艺确认表 + 钢材采购测算。"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session

from app.models.stamping import StampingPart, StampingProcess, StampingTailorWeldBlank
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.part.export.helpers import PartExportStyle
from app.services.stamping.part.export.process_confirm import ProcessConfirmExport
from app.services.stamping.part.export.steel_purchase import SteelPurchaseExport


class StampingPartExportService:
    """冲压零件导出：工艺确认表，以及钢材采购测算。"""

    def __init__(self) -> None:
        self.repository = StampingPartRepository()
        style = PartExportStyle()
        self._process_confirm = ProcessConfirmExport(self.repository, style)
        self._steel_purchase = SteelPurchaseExport(self._process_confirm, style)

    def export(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        year: int | None = None,
        month: int | None = None,
        include_expired: bool = False,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        return self._process_confirm.export(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            year=year,
            month=month,
            include_expired=include_expired,
            current_user=current_user,
        )

    def export_steel_purchase(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        return self._steel_purchase.export_steel_purchase(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            current_user=current_user,
        )

    def _write_headers(self, ws: Worksheet) -> None:
        return self._process_confirm._write_headers(ws)

    def _write_part_block(
        self,
        ws: Worksheet,
        *,
        start_row: int,
        seq_no: int,
        part: StampingPart,
        processes: list[StampingProcess],
        blanks: list[StampingTailorWeldBlank],
        zebra: bool,
        sketch_buffers: list[BytesIO],
    ) -> tuple[int, bool]:
        return self._process_confirm._write_part_block(
            ws,
            start_row=start_row,
            seq_no=seq_no,
            part=part,
            processes=processes,
            blanks=blanks,
            zebra=zebra,
            sketch_buffers=sketch_buffers,
        )

    def _write_steel_purchase_headers(self, ws: Worksheet) -> None:
        return self._steel_purchase._write_steel_purchase_headers(ws)

    def _write_steel_purchase_row(
        self,
        ws: Worksheet,
        *,
        excel_row: int,
        part: StampingPart,
        processes: list[StampingProcess],
        blank: StampingTailorWeldBlank | None,
        zebra: bool,
    ) -> None:
        return self._steel_purchase._write_steel_purchase_row(
            ws,
            excel_row=excel_row,
            part=part,
            processes=processes,
            blank=blank,
            zebra=zebra,
        )

    def _build_steel_purchase_workbook(
        self,
        parts: list[StampingPart],
        *,
        density: Decimal,
        location: str,
        stamping_supplier: str | None,
        vehicle_model: str | None,
        version: str | None,
    ) -> Workbook:
        return self._steel_purchase._build_steel_purchase_workbook(
            parts,
            density=density,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )

    def _workbook_to_plain_bytes(self, workbook: Workbook) -> bytes:
        return self._process_confirm._workbook_to_plain_bytes(workbook)
