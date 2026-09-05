"""总成核价计算报告 Excel 入口：拉日志、筛选核价卡、落文件名与水印字节。"""

import logging

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.common.export_watermark import workbook_to_xlsx_bytes
from app.schemas.vo.user_vo import UserVO
from app.services.costing.assembly_cost.calc.calc_log_service import (
    AssemblyCostCalcLogService,
)
from app.services.costing.assembly_cost.export.calc_report.builder import (
    CalcReportWorkbookBuilder,
)
from app.services.costing.assembly_cost.export.calc_report.filename import (
    build_calc_report_filename,
)
from app.services.costing.assembly_cost.export.calc_report.labels import TreeRootFilter
from app.services.costing.assembly_cost.export.calc_report.match import (
    match_calc_report_card,
)

logger = logging.getLogger("service.assembly_cost.calc_report_export")


class AssemblyCostCalcReportExportService:
    """把计算日志导出为与浅色报告页同口径的 Excel。"""

    def __init__(self, calc_log_service: AssemblyCostCalcLogService | None = None) -> None:
        self.calc_log_service = calc_log_service or AssemblyCostCalcLogService()
        self.builder = CalcReportWorkbookBuilder()

    def export(
        self,
        db: Session,
        *,
        log_id: int,
        keyword: str | None = None,
        status: str | None = None,
        level: int | None = None,
        tree_root: TreeRootFilter = "all",
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        log = self.calc_log_service.get_calc_log(db, log_id)
        cards = [
            card
            for card in log.cards
            if match_calc_report_card(
                card,
                keyword=keyword,
                status=status,
                level=level,
                tree_root=tree_root,
            )
        ]
        wb = Workbook()
        self.builder.write(
            wb,
            log,
            cards,
            keyword=keyword,
            status=status,
            level=level,
            tree_root=tree_root,
        )
        filename = build_calc_report_filename(log)
        content = workbook_to_xlsx_bytes(wb, current_user)
        logger.info(
            "导出计算报告 Excel: log_id=%s filename=%s cards=%d/%d",
            log_id,
            filename,
            len(cards),
            len(log.cards),
        )
        return content, filename
