"""采购价格导出开场：只读拼装价目表。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.schemas.dto.procurement_contract_report_dto import ProcurementContractReportQuery
from app.services.costing.procurement_contract_report.assemble import ReportBundle
from app.services.costing.procurement_contract_report.service import (
    ProcurementContractReportService,
)
from app.services.settings.system.settings_service import SettingsService


@dataclass(frozen=True, slots=True)
class ExportPrepContext:
    bundle: ReportBundle
    query: ProcurementContractReportQuery
    company_name: str
    remarks_template: str


def prepare_export(
    db: Session,
    query_service: ProcurementContractReportService,
    query: ProcurementContractReportQuery,
) -> ExportPrepContext:
    settings = SettingsService().get_config(db)
    return ExportPrepContext(
        bundle=query_service.build_report(db, query),
        query=query,
        company_name=settings.company_name,
        remarks_template=settings.procurement_agreement_remarks,
    )
