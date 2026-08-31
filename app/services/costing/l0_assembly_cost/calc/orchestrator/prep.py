"""计算开场：BOM 节点与上游价表。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.schemas.dto.l0_assembly_cost_dto import L0AssemblyCostCalcDTO
from app.services.costing.l0_assembly_cost.calc.calc_log_service import SCOPE_REQUIRED_MESSAGE
from app.services.costing.l0_assembly_cost.calc.orchestrator.deps import L0AssemblyCalcDeps
from app.services.costing.l0_assembly_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.l0_assembly_cost.calc.rollup import (
    RollupBomNode,
    RollupFinishedRates,
    RollupPackagingFee,
    RollupWeldingFee,
)


@dataclass(slots=True)
class CalcPrepContext:
    year: int
    month: int
    location: str
    vehicle_model: str
    bom_version: str
    snapshot_id: int
    children: dict[int | None, list[RollupBomNode]]
    l0_nodes: list[RollupBomNode]
    stamping_prices: dict[str, Decimal]
    annual_prices: dict[str, Decimal]
    welding_by_part: dict[str, RollupWeldingFee]
    packaging_by_part: dict[str, RollupPackagingFee]
    rates: RollupFinishedRates


def prepare_calc_run(
    db: Session,
    deps: L0AssemblyCalcDeps,
    dto: L0AssemblyCostCalcDTO,
    progress: ProgressNotifier,
) -> CalcPrepContext:
    year = dto.year
    month = dto.month
    location = dto.location.strip()
    vehicle_model = dto.vehicle_model.strip()
    bom_version = dto.bom_version.strip()
    if not location or not vehicle_model or not bom_version:
        raise BusinessException(SCOPE_REQUIRED_MESSAGE)

    progress.report(5, "加载 BOM…")
    snap = deps.bom_snapshot_repo.get_by_unique_key(db, location, vehicle_model, bom_version)
    if snap is None:
        raise BusinessException(f"无 BOM 快照: {location}/{vehicle_model}/{bom_version}")

    orm_nodes = deps.bom_node_repo.list_by_snapshot(db, snap.id)
    nodes = [
        RollupBomNode(
            id=n.id,
            parent_id=n.parent_id,
            level=int(n.level),
            part_number=n.part_number,
            part_name=n.part_name,
            qty=Decimal(str(n.qty if n.qty is not None else 1)),
            node_role=n.node_role,
            sort_no=n.sort_no or 0,
            sketch_url=getattr(n, "sketch_url", None),
        )
        for n in orm_nodes
    ]
    children: dict[int | None, list[RollupBomNode]] = {}
    for node in nodes:
        children.setdefault(node.parent_id, []).append(node)
    l0_nodes = sorted(
        [n for n in nodes if n.level == 0],
        key=lambda n: (n.sort_no, n.part_number),
    )
    if not l0_nodes:
        raise BusinessException("BOM 无 L0 成品节点")

    progress.report(15, "加载上游价表…")
    stamping_prices = {
        r.part_number: Decimal(str(r.unit_cost))
        for r in deps.stamping_cost_repo.list_calc_success_with_unit_cost(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
        )
    }
    annual_prices = {
        r.part_number: Decimal(str(r.unit_price))
        for r in deps.annual_price_repo.list_with_unit_price(db, location=location, year=year)
    }
    welding_by_part: dict[str, RollupWeldingFee] = {}
    for weld_row in deps.l0_welding_fee_repo.list_by_calc_scope(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        level=0,
    ):
        final = weld_row.final_welding_fee
        if final is None:
            final = weld_row.total_welding_fee or Decimal("0")
        welding_by_part[weld_row.part_number] = RollupWeldingFee(
            final_amount=Decimal(str(final)),
            other_fee=Decimal(str(weld_row.other_fee or 0)),
            missing_price_count=int(weld_row.missing_price_count or 0),
            welding_fee_id=weld_row.id,
            summary=None,
        )
    packaging_by_part: dict[str, RollupPackagingFee] = {}
    for pkg_row in deps.packaging_fee_repo.list_by_location_year(db, location=location, year=year):
        packaging_by_part[pkg_row.part_number] = RollupPackagingFee(
            unit_transport_fee=Decimal(str(pkg_row.unit_transport_fee)),
            warehouse_bundling_fee=Decimal(str(pkg_row.other_fee or 0)),
        )

    rates = RollupFinishedRates(
        finance_rate=deps.settings_service.get_finished_finance_rate(db),
        management_rate=deps.settings_service.get_finished_management_rate(db),
        scrap_rate=deps.settings_service.get_finished_scrap_rate(db),
        pretax_profit_rate=deps.settings_service.get_finished_pretax_profit_rate(db),
    )
    return CalcPrepContext(
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        snapshot_id=snap.id,
        children=children,
        l0_nodes=l0_nodes,
        stamping_prices=stamping_prices,
        annual_prices=annual_prices,
        welding_by_part=welding_by_part,
        packaging_by_part=packaging_by_part,
        rates=rates,
    )
