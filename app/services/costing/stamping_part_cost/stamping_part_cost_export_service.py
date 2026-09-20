"""冲压零件价格核算 Excel 导出（门面）。"""

from __future__ import annotations

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.stamping_part_cost.export.process_sheet import (
    export_process_sheet,
    write_process_sheet_to_workbook,
)
from app.services.masterdata.supplier import SupplierService

EXPORT_VEHICLE_REQUIRED_MESSAGE = "导出须选定项目。"


def require_export_vehicle_model(vehicle_model: str | None) -> str:
    value = (vehicle_model or "").strip()
    if not value:
        raise BusinessException(EXPORT_VEHICLE_REQUIRED_MESSAGE)
    return value


class StampingPartCostExportService:
    """导出冲压零件核价结果（材料费 + 加工费 + 模具费 + 检具费）。"""

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
        vehicle_model: str,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        vehicle_value = require_export_vehicle_model(vehicle_model)
        rows = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            stamping_suppliers=SupplierService().names_for_query(db, stamping_supplier),
            vehicle_model=vehicle_value,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        return export_process_sheet(
            db,
            rows,
            bom_snapshot_repo=self.bom_snapshot_repo,
            bom_node_repo=self.bom_node_repo,
            steel_price_repo=self.steel_price_repo,
            scrap_price_repo=self.scrap_price_repo,
            process_fee_repo=self.process_fee_repo,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_value,
            version=version,
            current_user=current_user,
        )

    def write_to_workbook(
        self,
        wb: Workbook,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        sheet_title: str = "冲压核价结果",
    ) -> tuple[str, int]:
        vehicle_value = require_export_vehicle_model(vehicle_model)
        rows = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            stamping_suppliers=SupplierService().names_for_query(db, stamping_supplier),
            vehicle_model=vehicle_value,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        return write_process_sheet_to_workbook(
            wb,
            db,
            rows,
            bom_snapshot_repo=self.bom_snapshot_repo,
            bom_node_repo=self.bom_node_repo,
            steel_price_repo=self.steel_price_repo,
            scrap_price_repo=self.scrap_price_repo,
            process_fee_repo=self.process_fee_repo,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_value,
            version=version,
            sheet_title=sheet_title,
        )
