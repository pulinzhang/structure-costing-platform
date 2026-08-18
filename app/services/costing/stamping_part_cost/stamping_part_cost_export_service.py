"""冲压零件价格核算 Excel 导出（门面）。"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.services.costing.stamping_part_cost.export.detail import export_detail
from app.services.costing.stamping_part_cost.export.process_sheet import (
    export_process_sheet,
)

ExportFormat = Literal["detail", "process_sheet"]


class StampingPartCostExportService:
    """导出零件价格核算结果。"""

    def __init__(self) -> None:
        self.repository = StampingPartCostRepository()
        self.bom_snapshot_repo = BomSnapshotRepository()
        self.bom_node_repo = BomNodeRepository()
        self.steel_price_repo = SteelPriceRepository()
        self.scrap_price_repo = StampingScrapPriceRepository()
        self.process_fee_repo = StampingProcessFeeRepository()

    def export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        export_format: ExportFormat = "process_sheet",
    ) -> tuple[bytes, str]:
        rows = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        if export_format == "detail":
            return export_detail(
                db,
                rows,
                steel_price_repo=self.steel_price_repo,
                scrap_price_repo=self.scrap_price_repo,
                process_fee_repo=self.process_fee_repo,
            )
        return export_process_sheet(
            db,
            rows,
            bom_snapshot_repo=self.bom_snapshot_repo,
            bom_node_repo=self.bom_node_repo,
            steel_price_repo=self.steel_price_repo,
            scrap_price_repo=self.scrap_price_repo,
            process_fee_repo=self.process_fee_repo,
        )
