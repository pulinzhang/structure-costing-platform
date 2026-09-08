"""L0 核对导出开场：筛选取数与表头摘要。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.bom import BomWeldingProcessBreakdownNode
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.services.bom.welding_process_breakdown.export.values import filter_summary


@dataclass(frozen=True, slots=True)
class ExportPrepContext:
    nodes: list[BomWeldingProcessBreakdownNode]
    filter_text: str
    location: str | None
    vehicle_model: str | None
    bom_version: str | None
    process_line_count_eq: int | None


def prepare_export(
    db: Session,
    repository: BomWeldingProcessBreakdownRepository,
    *,
    location: str | None,
    customer_name: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    part_number: str | None,
    process_line_count_eq: int | None,
) -> ExportPrepContext:
    nodes = repository.list_l0_for_export(
        db,
        location=location,
        customer_name=customer_name,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        part_number=part_number,
        process_line_count_eq=process_line_count_eq,
    )
    return ExportPrepContext(
        nodes=nodes,
        filter_text=filter_summary(
            location=location,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            process_line_count_eq=process_line_count_eq,
        ),
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        process_line_count_eq=process_line_count_eq,
    )
