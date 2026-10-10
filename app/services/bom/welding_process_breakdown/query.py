"""焊接工艺拆解：列表分页、节点详情与旁证。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.bom.welding_standard_process import all_standard_process_names
from app.exceptions.base import NotFoundException
from app.models.bom import BomWeldingProcessBreakdownNode
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
    WeldingBreakdownFilterSummary,
    WeldingBreakdownListFilters,
)
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownQuery,
)
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    BomWeldingProcessBreakdownNodeVO,
    WeldingNodeEvidenceVO,
)
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.welding_process_breakdown.bom_tree import build_children_map
from app.services.bom.welding_process_breakdown.evidence import build_node_evidence
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.service import VehicleModelService


def overlay_breakdown_vos(
    db: Session,
    rows: list[BomWeldingProcessBreakdownNode],
) -> list[BomWeldingProcessBreakdownNodeVO]:
    overlays = BomPeriodService().map_tree_root_version_by_node_id(
        db,
        [int(row.source_node_id) for row in rows if row.source_node_id],
    )
    result: list[BomWeldingProcessBreakdownNodeVO] = []
    for row in rows:
        vo = BomWeldingProcessBreakdownNodeVO.model_validate(row)
        if row.source_node_id:
            overlay = overlays.get(int(row.source_node_id))
            if overlay:
                vo.bom_version = overlay
        result.append(vo)
    return result


def resolve_breakdown_tree_root_version(
    db: Session,
    row: BomWeldingProcessBreakdownNode,
) -> str:
    return overlay_breakdown_vos(db, [row])[0].bom_version or ""


def build_list_summary(
    repository: BomWeldingProcessBreakdownRepository,
    db: Session,
    *,
    location: str | None = None,
    locations: list[str] | None = None,
    customer_name: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    part_number: str | None,
    level: int | None,
    audit_status: str | None,
    parse_status: str | None,
) -> WeldingBreakdownFilterSummary:
    """HUD：列表口径汇总（不含工艺数钻取）+ L0 工艺数=0（不受层级/工艺数筛选影响）。"""
    source_node_ids = BomPeriodService().node_ids_for_l0_version(
        db,
        bom_version=bom_version,
        location=location,
        locations=locations,
        vehicle_model=vehicle_model,
    )
    summary = repository.summarize_by_filters(
        db,
        location=location,
        locations=locations,
        customer_name=customer_name,
        vehicle_model=vehicle_model,
        source_node_ids=source_node_ids,
        part_number=part_number,
        level=level,
        audit_status=audit_status,
        parse_status=parse_status,
    )
    summary["l0_zero_process_count"] = repository.count_by_filters(
        db,
        location=location,
        locations=locations,
        customer_name=customer_name,
        vehicle_model=vehicle_model,
        source_node_ids=source_node_ids,
        part_number=part_number,
        level=0,
        audit_status=audit_status,
        parse_status=parse_status,
        process_line_count_eq=0,
    )
    return summary


def paginate_nodes(
    repository: BomWeldingProcessBreakdownRepository,
    db: Session,
    query: BomWeldingProcessBreakdownQuery,
    *,
    location_service: LocationService,
    vehicle_service: VehicleModelService,
) -> tuple[list[BomWeldingProcessBreakdownNodeVO], int, WeldingBreakdownListFilters]:
    skip = (query.page - 1) * query.size
    audit_status = query.audit_status.strip() if query.audit_status else None
    locations: list[str] | None = None
    if query.location:
        locations = location_service.expand_for_query(db, query.location)
        if not locations:
            filters: WeldingBreakdownListFilters = {
                "locations": location_service.list_registered(db),
                "customer_names": repository.get_distinct_customer_names(db),
                "vehicle_models": vehicle_service.list_filter_codes(db, query.location),
                "bom_versions": [],
                "standard_process_names": all_standard_process_names(),
                "audit_status": audit_status,
                "summary": {
                    "total_count": 0,
                    "pending_count": 0,
                    "approved_count": 0,
                    "l0_count": 0,
                    "l0_zero_process_count": 0,
                },
            }
            return [], 0, filters
    source_node_ids = BomPeriodService().node_ids_for_l0_version(
        db,
        bom_version=query.bom_version,
        locations=locations,
        vehicle_model=query.vehicle_model,
    )
    rows, total = repository.paginate(
        db,
        locations=locations,
        customer_name=query.customer_name,
        vehicle_model=query.vehicle_model,
        source_node_ids=source_node_ids,
        part_number=query.part_number,
        level=query.level,
        audit_status=audit_status,
        parse_status=query.parse_status,
        process_line_count_eq=query.process_line_count_eq,
        skip=skip,
        limit=query.size,
    )
    filters = {
        "locations": location_service.list_registered(db),
        "customer_names": repository.get_distinct_customer_names(db),
        "vehicle_models": vehicle_service.list_filter_codes(db, query.location),
        "bom_versions": BomPeriodService().list_l0_versions(
            db,
            locations=locations,
            vehicle_model=query.vehicle_model,
        ),
        "standard_process_names": all_standard_process_names(),
        "audit_status": audit_status,
        "summary": build_list_summary(
            repository,
            db,
            locations=locations,
            customer_name=query.customer_name,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            part_number=query.part_number,
            level=query.level,
            audit_status=audit_status,
            parse_status=query.parse_status,
        ),
    }
    return (
        overlay_breakdown_vos(db, rows),
        total,
        filters,
    )


def build_evidence_vo(
    repository: BomWeldingProcessBreakdownRepository,
    node_repository: BomNodeRepository,
    db: Session,
    row: BomWeldingProcessBreakdownNode,
) -> WeldingNodeEvidenceVO:
    scope_version = resolve_breakdown_tree_root_version(db, row)
    source_node_ids = BomPeriodService().node_ids_for_l0_version(
        db,
        bom_version=scope_version,
        location=row.location,
        vehicle_model=row.vehicle_model,
    )
    scope_nodes = repository.list_by_scope(
        db,
        location=row.location,
        vehicle_model=row.vehicle_model,
        source_node_ids=source_node_ids,
    )
    children_map = None
    if row.snapshot_id is not None:
        bom_nodes = node_repository.list_by_snapshot(db, row.snapshot_id)
        children_map = build_children_map(bom_nodes)
    return build_node_evidence(
        row,
        scope_nodes=scope_nodes,
        children_map=children_map,
    )


def get_node(
    repository: BomWeldingProcessBreakdownRepository,
    node_repository: BomNodeRepository,
    db: Session,
    node_id: int,
) -> BomWeldingProcessBreakdownNodeVO:
    row = repository.get_node_by_id(db, node_id)
    if not row:
        raise NotFoundException("记录不存在")
    vo = overlay_breakdown_vos(db, [row])[0]
    vo.evidence = build_evidence_vo(repository, node_repository, db, row)
    return vo
