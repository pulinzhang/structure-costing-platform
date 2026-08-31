"""计算开场：焊接单价与拆解节点（按 levels 过滤）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.bom import BomWeldingProcessBreakdownNode
from app.models.bom.welding_unit_price import BomWeldingUnitPrice
from app.repositories.bom.bom_repository import BomSnapshotRepository
from app.schemas.dto.bom_welding_fee_dto import BomWeldingFeeCalcDTO
from app.services.bom.welding_fee.calc.orchestrator.deps import WeldingFeeCalcDeps
from app.services.bom.welding_fee.calc.orchestrator.progress import ProgressNotifier


@dataclass(slots=True)
class CalcPrepContext:
    year: int
    location: str
    vehicle_model: str
    bom_version: str
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
    location = dto.location.strip()
    vehicle_model = dto.vehicle_model.strip()
    bom_version = dto.bom_version.strip()
    started_at = now()
    detail_lines = [
        f"开始计算 year={year} location={location} "
        f"vehicle={vehicle_model} bom_version={bom_version}"
    ]

    progress.report(5, "加载焊接单价...")
    prices = deps.unit_price_repo.list_by_location_year(db, location, year)
    if not prices:
        raise BusinessException(f"基地「{location}」年度 {year} 无焊接单价数据，请先维护焊接单价")
    price_map: dict[str, BomWeldingUnitPrice] = {p.item_name: p for p in prices}
    detail_lines.append(f"焊接单价 {len(prices)} 条")

    progress.report(10, "加载焊接工艺拆解...")
    all_nodes = deps.breakdown_repo.list_by_scope(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
    )
    selected_levels = [int(level) for level in (dto.levels or []) if level is not None]
    if selected_levels:
        wanted = set(selected_levels)
        nodes = [node for node in all_nodes if int(node.level) in wanted]
        detail_lines.append(f"指定层级 {sorted(wanted)} 节点 {len(nodes)} 个")
    else:
        nodes = list(all_nodes)
        present = sorted({int(node.level) for node in nodes})
        detail_lines.append(f"拆解节点 {len(nodes)} 个（层级 {present}）")

    if not nodes:
        raise BusinessException(
            f"基地「{location}」车型「{vehicle_model}」版本「{bom_version}」"
            f"下未找到焊接工艺拆解节点"
        )

    source_excel_filename = None
    source_sheet_name = None
    snapshot_id = next(
        (node.snapshot_id for node in nodes if node.snapshot_id is not None),
        None,
    )
    if snapshot_id is not None:
        snapshot = BomSnapshotRepository().get_by_id(db, snapshot_id)
        if snapshot is not None:
            source_excel_filename = (snapshot.source_filename or "").strip() or None
            source_sheet_name = (snapshot.source_sheet_name or "").strip() or None

    return CalcPrepContext(
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        price_map=price_map,
        nodes=nodes,
        started_at=started_at,
        detail_lines=detail_lines,
        source_excel_filename=source_excel_filename,
        source_sheet_name=source_sheet_name,
    )
