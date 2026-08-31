"""成品核价就绪统计。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.l0_assembly_cost_vo import L0AssemblyCostCalcReadyVO
from app.services.costing.l0_assembly_cost.calc.orchestrator.deps import L0AssemblyCalcDeps


def collect_calc_ready(
    db: Session,
    deps: L0AssemblyCalcDeps,
    *,
    year: int,
    month: int,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> L0AssemblyCostCalcReadyVO:
    location = location.strip()
    vehicle_model = vehicle_model.strip()
    bom_version = bom_version.strip()
    snap = deps.bom_snapshot_repo.get_by_unique_key(db, location, vehicle_model, bom_version)
    l0_count = 0
    if snap is not None:
        l0_count = deps.bom_node_repo.count_by_snapshot_and_level(db, snap.id, level=0)
    stamping_n = deps.stamping_cost_repo.count_calc_success_with_unit_cost(
        db,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
    )
    annual_n = deps.annual_price_repo.count_with_unit_price(db, location=location, year=year)
    weld_n = deps.l0_welding_fee_repo.count_by_calc_scope(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
    )
    pkg_n = deps.packaging_fee_repo.count_by_location_year(db, location=location, year=year)
    ready = l0_count > 0 and (stamping_n > 0 or annual_n > 0)
    message = None
    if snap is None:
        message = "未找到对应 BOM 快照"
        ready = False
    elif l0_count == 0:
        message = "BOM 无 L0 成品"
        ready = False
    elif stamping_n == 0 and annual_n == 0:
        message = "无冲压价且无年度价，无法计算"
        ready = False
    return L0AssemblyCostCalcReadyVO(
        l0_count=l0_count,
        stamping_price_count=stamping_n,
        annual_price_count=annual_n,
        welding_fee_count=weld_n,
        packaging_fee_count=pkg_n,
        bom_version=bom_version,
        ready=ready,
        message=message,
    )
