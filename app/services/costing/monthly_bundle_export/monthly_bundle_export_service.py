"""月度核价合册导出：同一 Workbook 串联各切片 write_to_workbook。"""

from __future__ import annotations

import logging
from io import BytesIO

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.services.bom.annual_part_price_export_service import BomAnnualPartPriceExportService
from app.services.bom.packaging_transport_fee_export_service import (
    BomPackagingTransportFeeExportService,
)
from app.services.bom.welding_unit_price_export_service import BomWeldingUnitPriceExportService
from app.services.costing.l0_assembly_cost.export.l0_assembly_cost_export_service import (
    L0AssemblyCostExportService,
)
from app.services.costing.monthly_bundle_export.cover_sheet import write_cover_sheet
from app.services.costing.steel_price.steel_price_export_service import SteelPriceExportService
from app.services.costing.stamping_part_cost.stamping_part_cost_export_service import (
    StampingPartCostExportService,
)
from app.services.stamping.stamping_process_fee_export_service import (
    StampingProcessFeeExportService,
)

logger = logging.getLogger("service.monthly_bundle_export")


class MonthlyBundleExportService:
    """
    按年/月/基地/车型/BOM 版本导出「核对合册」。

    编排归属 costing（下游组合上游导出）；各 sheet 仍由对应切片 ExportService 写入。
    """

    def __init__(self) -> None:
        self.steel_price = SteelPriceExportService()
        self.process_fee = StampingProcessFeeExportService()
        self.part_cost = StampingPartCostExportService()
        self.annual_part_price = BomAnnualPartPriceExportService()
        self.packaging = BomPackagingTransportFeeExportService()
        self.welding_unit_price = BomWeldingUnitPriceExportService()
        self.l0_assembly = L0AssemblyCostExportService()

    def export(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        stamping_supplier: str | None = None,
    ) -> tuple[bytes, str]:
        """
        生成合册 Excel。

        bom_version 仅用于 BOM/成品侧（成品核价、焊接费）。
        冲压零件核价与加工费不传版本：工艺版本与 BOM 版本本就不一致。
        """
        location = (location or "").strip()
        vehicle_model = (vehicle_model or "").strip()
        bom_version = (bom_version or "").strip()
        if not location or not vehicle_model or not bom_version:
            raise BusinessException("基地、项目、版本不能为空")
        stamping_supplier = (stamping_supplier or "").strip() or None

        wb = Workbook()
        sheet_counts: dict[str, int] = {}

        cover_title = write_cover_sheet(
            wb,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            stamping_supplier=stamping_supplier,
        )
        sheet_counts[cover_title] = 1

        # 成品核价（含一览/材料明细/焊接费/间接费用）→ 冲压零件核价…
        title, count = self.l0_assembly.write_to_workbook(
            wb,
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        sheet_counts[title] = count

        title, count = self.part_cost.write_to_workbook(
            wb,
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
        )
        sheet_counts[title] = count

        title, count = self.process_fee.write_to_workbook(
            wb,
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
        )
        sheet_counts[title] = count

        title, count = self.steel_price.write_to_workbook(
            wb,
            db,
            year=year,
            month=month,
            location=location,
        )
        sheet_counts[title] = count

        title, count = self.annual_part_price.write_to_workbook(
            wb,
            db,
            location=location,
            year=year,
        )
        sheet_counts[title] = count

        title, count = self.packaging.write_to_workbook(
            wb,
            db,
            location=location,
            year=year,
            vehicle_model=vehicle_model,
        )
        sheet_counts[title] = count

        title, count = self.welding_unit_price.write_to_workbook(
            wb,
            db,
            location=location,
            year=year,
        )
        sheet_counts[title] = count

        stamp = now().strftime("%Y%m%d_%H%M%S")
        safe_version = bom_version.replace("/", "-").replace("\\", "-")
        filename = (
            f"核对合册_{year}年{month}月_{location}_" f"{vehicle_model}_{safe_version}_{stamp}.xlsx"
        )
        output = BytesIO()
        wb.save(output)
        logger.info(
            "月度核对合册导出完成: filename=%s sheets=%s",
            filename,
            sheet_counts,
        )
        return output.getvalue(), filename
