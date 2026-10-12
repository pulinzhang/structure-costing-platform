"""计算开场：焊接单价与拆解节点（按 L0 树根年交集 + levels 过滤）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.bom import BomWeldingProcessBreakdownNode
from app.models.bom.welding_unit_price import BomWeldingUnitPrice
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.schemas.dto.bom_welding_fee_dto import BomWeldingFeeCalcDTO
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.welding_fee.calc.orchestrator.deps import WeldingFeeCalcDeps
from app.services.bom.welding_fee.calc.orchestrator.messages import (
    format_missing_breakdown,
    format_missing_prices,
    format_no_nodes,
    format_no_overlap,
    format_nodes_in_scope,
    format_prep_opening,
    format_prices_loaded,
)
from app.services.bom.welding_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.masterdata.vehicle_model.service import VehicleModelService


@dataclass(slots=True)
class CalcPrepContext:
    year: int
    location: str
    vehicle_model: str
    price_map: dict[str, BomWeldingUnitPrice]
    nodes: list[BomWeldingProcessBreakdownNode]
    started_at: datetime
    detail_lines: list[str]
    source_excel_filename: str | None = None
    source_sheet_name: str | None = None


def prepare_calc_run(
    db: Session,
    deps: WeldingFeeCalcDeps,
    dto: BomWeldingFeeCalcDTO,
    progress: ProgressNotifier,
) -> CalcPrepContext:
    year = dto.year
    location, vehicle_model = VehicleModelService().require_overlaps_year(
        db, dto.location, dto.vehicle_model, year
    )
    started_at = now()
    detail_lines = [format_prep_opening(year, location, vehicle_model)]

    progress.report(5, "正在读取焊接单价…")
    prices = deps.unit_price_repo.list_by_location_year(db, location, year)
    if not prices:
        raise BusinessException(format_missing_prices(location, year))
    price_map: dict[str, BomWeldingUnitPrice] = {p.item_name: p for p in prices}
    detail_lines.append(format_prices_loaded(len(prices)))

    progress.report(10, "正在读取已经拆好的工艺…")
    if not deps.breakdown_repo.exists_by_location_vehicle(
        db, location=location, vehicle_model=vehicle_model
    ):
        raise BusinessException(format_missing_breakdown(location, vehicle_model))
    all_nodes = deps.breakdown_repo.list_by_source_node_ids(
        db,
        list(
            BomPeriodService().node_ids_overlapping_year(
                db, location=location, vehicle_model=vehicle_model, year=year
            )
        ),
    )
    if not all_nodes:
        raise BusinessException(format_no_overlap(location, vehicle_model, year))
    selected_levels = [int(level) for level in (dto.levels or []) if level is not None]
    if selected_levels:
        wanted = set(selected_levels)
        nodes = [node for node in all_nodes if int(node.level) in wanted]
    else:
        nodes = list(all_nodes)
    if not nodes:
        raise BusinessException(format_no_nodes(location, vehicle_model))
    detail_lines.append(format_nodes_in_scope(len(nodes), [int(node.level) for node in nodes]))

    source_excel_filename = None
    source_sheet_name = None
    snapshot_id: int | None = None
    for node in nodes:
        raw = getattr(node, "snapshot_id", None)
        if isinstance(raw, int):
            snapshot_id = raw
            break
    if snapshot_id is not None:
        snapshot = BomSnapshotRepository().get_by_id(db, snapshot_id)
        if snapshot is not None:
            source_excel_filename = (snapshot.source_filename or "").strip() or None
            source_sheet_name = (snapshot.source_sheet_name or "").strip() or None

    return CalcPrepContext(
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        price_map=price_map,
        nodes=nodes,
        started_at=started_at,
        detail_lines=detail_lines,
        source_excel_filename=source_excel_filename,
        source_sheet_name=source_sheet_name,
    )
