"""计算开场：焊接单价与成品拆解节点。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.bom import BomWeldingProcessBreakdownNode
from app.models.bom.welding_unit_price import BomWeldingUnitPrice
from app.schemas.dto.bom_l0_welding_fee_dto import BomL0WeldingFeeCalcDTO
from app.services.bom.l0_welding_fee.calc.orchestrator.deps import L0WeldingFeeCalcDeps
from app.services.bom.l0_welding_fee.calc.orchestrator.progress import ProgressNotifier


@dataclass(slots=True)
class CalcPrepContext:
    year: int
    location: str
    vehicle_model: str
    bom_version: str
    price_map: dict[str, BomWeldingUnitPrice]
    l0_nodes: list[BomWeldingProcessBreakdownNode]
    started_at: datetime
    detail_lines: list[str]


def prepare_calc_run(
    db: Session,
    deps: L0WeldingFeeCalcDeps,
    dto: BomL0WeldingFeeCalcDTO,
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

    progress.report(10, "加载成品焊接工艺拆解...")
    all_nodes = deps.breakdown_repo.list_by_scope(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
    )
    l0_nodes = [n for n in all_nodes if n.level == 0]
    if not l0_nodes:
        raise BusinessException(
            f"基地「{location}」车型「{vehicle_model}」版本「{bom_version}」"
            f"下未找到成品焊接工艺拆解"
        )
    detail_lines.append(f"成品节点 {len(l0_nodes)} 个")

    return CalcPrepContext(
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        price_map=price_map,
        l0_nodes=l0_nodes,
        started_at=started_at,
        detail_lines=detail_lines,
    )
