"""月度核对导出：同一 Workbook 串联各切片 write_to_workbook。"""

from __future__ import annotations

import logging

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.export_watermark import workbook_to_xlsx_bytes
from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.schemas.vo.user_vo import UserVO
from app.services.bom.annual_part_price.export_service import BomAnnualPartPriceExportService
from app.services.bom.packaging_transport_fee.export_service import (
    BomPackagingTransportFeeExportService,
)
from app.services.bom.welding_unit_price.export_service import BomWeldingUnitPriceExportService
from app.services.costing.assembly_cost.export.assembly_cost_export_service import (
    AssemblyCostExportService,
)
from app.services.costing.monthly_bundle_export.cover_sheet import write_cover_sheet
from app.services.costing.stamping_part_cost.stamping_part_cost_export_service import (
    StampingPartCostExportService,
)
from app.services.costing.steel_price.steel_price_export_service import SteelPriceExportService
from app.services.stamping.stamping_process_fee_export_service import (
    StampingProcessFeeExportService,
)

logger = logging.getLogger("service.monthly_bundle_export")


class MonthlyBundleExportService:
    """
    按年/月/基地/项目导出「月度核对导出」。

    编排归属 costing（下游组合上游导出）；各 sheet 仍由对应切片 ExportService 写入。
    版本可选：工程变更后同月可有多个节点版本字，空=该月该项目全部成品卡。
    """

    def __init__(self) -> None:
        self.steel_price = SteelPriceExportService()
        self.process_fee = StampingProcessFeeExportService()
        self.part_cost = StampingPartCostExportService()
        self.annual_part_price = BomAnnualPartPriceExportService()
        self.packaging = BomPackagingTransportFeeExportService()
        self.welding_unit_price = BomWeldingUnitPriceExportService()
        self.assembly = AssemblyCostExportService()

    def export(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str | None = None,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        """
        生成月度核对 Excel。

        bom_version 可选；有则只导出该节点版本字的成品卡，空则该月全部。
        冲压零件核价与加工费不传版本：工艺版本与 BOM 版本本就不一致。
        冲压侧按整车导出，不按工厂切分。
        """
        location = (location or "").strip()
        vehicle_model = (vehicle_model or "").strip()
        bom_version = (bom_version or "").strip() or None
        if not location or not vehicle_model:
            raise BusinessException("基地、项目不能为空")

        wb = Workbook()
        sheet_counts: dict[str, int] = {}

        cover_title = write_cover_sheet(
            wb,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        sheet_counts[cover_title] = 1

        # 成品核价（含一览/材料明细/焊接费/间接费用）→ 冲压零件核价…
        title, count = self.assembly.write_to_workbook(
            wb,
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            view="finance",
        )
        sheet_counts[title] = count

        title, count = self.part_cost.write_to_workbook(
            wb,
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
        )
        sheet_counts[title] = count

        title, count = self.process_fee.write_to_workbook(
            wb,
            db,
            year=year,
            location=location,
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
        version_part = ""
        if bom_version:
            safe_version = bom_version.replace("/", "-").replace("\\", "-")
            version_part = f"_{safe_version}"
        filename = (
            f"月度核对导出_{year}年{month}月_{location}_"
            f"{vehicle_model}{version_part}_{stamp}.xlsx"
        )
        content = workbook_to_xlsx_bytes(wb, current_user)
        logger.info(
            "月度核对导出完成: filename=%s sheets=%s",
            filename,
            sheet_counts,
        )
        return content, filename
