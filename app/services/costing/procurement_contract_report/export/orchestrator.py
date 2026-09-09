"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

采购价格协议导出 — 编排器（prepare → engine → persist）
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.dto.procurement_contract_report_dto import ProcurementContractReportQuery
from app.services.costing.procurement_contract_report.export.persist import persist_export
from app.services.costing.procurement_contract_report.export.prep import prepare_export
from app.services.costing.procurement_contract_report.export.workbook import (
    AgreementWorkbookEngine,
)
from app.services.costing.procurement_contract_report.service import (
    ProcurementContractReportService,
)


class ProcurementContractReportExportOrchestrator:
    """导出编排：准备取数 → 交给 workbook 引擎渲染 → 落盘字节与文件名。"""

    def __init__(self) -> None:
        self.query_service = ProcurementContractReportService()
        self.workbook_engine = AgreementWorkbookEngine()

    def export(
        self,
        db: Session,
        query: ProcurementContractReportQuery,
    ) -> tuple[bytes, str]:
        ctx = prepare_export(db, self.query_service, query)
        workbook = self.workbook_engine.run(ctx.bundle, ctx.company_name)
        return persist_export(ctx, workbook)
