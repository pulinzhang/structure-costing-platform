"""L0 核对导出收尾：文件名与日志（不写库）。"""

from __future__ import annotations

import logging

from app.common.timezone import now
from app.services.bom.welding_process_breakdown.export.prep import ExportPrepContext
from app.services.bom.welding_process_breakdown.export.values import build_filename

logger = logging.getLogger("service.bom.welding_process_breakdown.export")


def persist_export(
    ctx: ExportPrepContext,
    content: bytes,
    export_row_count: int,
) -> tuple[bytes, str]:
    stamp = now().strftime("%Y%m%d_%H%M%S")
    filename = build_filename(
        location=ctx.location,
        vehicle_model=ctx.vehicle_model,
        bom_version=ctx.bom_version,
        stamp=stamp,
    )
    logger.info(
        "导出 L0 工艺核对 %s 行（%s 个 L0） " "location=%s model=%s ver=%s process_eq=%s -> %s",
        export_row_count,
        len(ctx.nodes),
        ctx.location,
        ctx.vehicle_model,
        ctx.bom_version,
        ctx.process_line_count_eq,
        filename,
    )
    return content, filename
