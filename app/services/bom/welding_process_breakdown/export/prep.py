"""L0 核对导出开场：筛选取数与表头摘要。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.bom import BomWeldingProcessBreakdownNode
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.welding_process_breakdown.export.values import filter_summary


@dataclass(frozen=True, slots=True)
class ExportPrepContext:
    nodes: list[BomWeldingProcessBreakdownNode]
    filter_text: str
    location: str | None
    vehicle_model: str | None
    bom_version: str | None
    process_line_count_eq: int | None
    version_by_node_id: dict[int, str]


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
        source_node_ids=BomPeriodService().node_ids_for_l0_version(
            db,
            bom_version=bom_version,
            location=location,
            vehicle_model=vehicle_model,
        ),
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
        version_by_node_id=_overlay_versions_by_breakdown_id(db, nodes),
    )


def _overlay_versions_by_breakdown_id(
    db: Session,
    nodes: list[BomWeldingProcessBreakdownNode],
) -> dict[int, str]:
    by_source = BomPeriodService().map_tree_root_version_by_node_id(
        db,
        [int(node.source_node_id) for node in nodes if node.source_node_id],
    )
    result: dict[int, str] = {}
    for node in nodes:
        if not node.source_node_id:
            continue
        overlay = by_source.get(int(node.source_node_id))
        if overlay:
            result[int(node.id)] = overlay
    return result
