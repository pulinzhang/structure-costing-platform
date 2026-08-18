"""
L0 核对导出 — 编排器（查库 → 渲染工作簿 → 文件名）

不负责列布局 / 样式 / openpyxl 细节；那些分别在 columns / styles / workbook。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.services.bom.welding_process_breakdown.export.values import (
    build_filename,
    filter_summary,
)
from app.services.bom.welding_process_breakdown.export.workbook import (
    L0CheckWorkbookBuilder,
)

logger = logging.getLogger("service.bom.welding_process_breakdown.export")


class BomWeldingProcessBreakdownExportOrchestrator:
    """导出编排：按筛选取 L0 → 交给 workbook 渲染 → 组装文件名。"""

    def __init__(self) -> None:
        self.repository = BomWeldingProcessBreakdownRepository()
        self.workbook_builder = L0CheckWorkbookBuilder()

    def export(
        self,
        db: Session,
        *,
        location: str | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> tuple[bytes, str]:
        nodes = self.repository.list_l0_for_export(
            db,
            location=location,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            process_line_count_eq=process_line_count_eq,
        )

        content, export_row_count = self.workbook_builder.build(
            nodes,
            filter_text=filter_summary(
                location=location,
                customer_name=customer_name,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                part_number=part_number,
                process_line_count_eq=process_line_count_eq,
            ),
        )

        stamp = now().strftime("%Y%m%d_%H%M%S")
        filename = build_filename(
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            stamp=stamp,
        )

        logger.info(
            "导出 L0 工艺核对 %s 行（%s 个 L0） "
            "location=%s model=%s ver=%s process_eq=%s -> %s",
            export_row_count,
            len(nodes),
            location,
            vehicle_model,
            bom_version,
            process_line_count_eq,
            filename,
        )
        return content, filename
