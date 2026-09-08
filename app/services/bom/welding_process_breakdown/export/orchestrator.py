"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

L0 核对导出 — 编排器（prepare → workbook → persist）
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_process_breakdown.export.persist import persist_export
from app.services.bom.welding_process_breakdown.export.prep import prepare_export
from app.services.bom.welding_process_breakdown.export.workbook import (
    L0CheckWorkbookBuilder,
)


class BomWeldingProcessBreakdownExportOrchestrator:
    """导出编排：准备取数 → 交给 workbook 渲染 → 组装文件名。"""

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
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        ctx = prepare_export(
            db,
            self.repository,
            location=location,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            process_line_count_eq=process_line_count_eq,
        )
        content, export_row_count = self.workbook_builder.build(
            ctx.nodes,
            filter_text=ctx.filter_text,
            current_user=current_user,
        )
        return persist_export(ctx, content, export_row_count)
