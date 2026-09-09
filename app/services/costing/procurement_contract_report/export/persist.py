"""采购价格导出收尾：文件名、日志（不写业务库、不加盖水印）。"""

from __future__ import annotations

import logging
from io import BytesIO

from openpyxl import Workbook

from app.services.costing.procurement_contract_report.export.prep import ExportPrepContext
from app.services.costing.procurement_contract_report.export.values import build_filename

logger = logging.getLogger("service.costing.procurement_contract_report.export")


def persist_export(ctx: ExportPrepContext, workbook: Workbook) -> tuple[bytes, str]:
    filename = build_filename(ctx.bundle)
    buffer = BytesIO()
    workbook.save(buffer)
    logger.info(
        "导出批量零部件价格协议 view=%s prep=%s price=%s location=%s model=%s ver=%s -> %s",
        ctx.query.view,
        len(ctx.bundle.prep_rows),
        len(ctx.bundle.price_rows),
        ctx.query.location,
        ctx.query.vehicle_model,
        ctx.query.bom_version,
        filename,
    )
    return buffer.getvalue(), filename
