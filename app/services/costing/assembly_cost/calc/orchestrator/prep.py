"""计算开场：BOM 节点、核价主体与上游已落库价表。"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.bom.node_order import bom_node_order_from
from app.exceptions.base import BusinessException
from app.models.costing import StampingPartCost
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.assembly_cost_dto import AssemblyCostCalcDTO
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.procurement_object.classify import SECTION_OBJECT
from app.services.costing.assembly_cost.calc.calc_log_service import SCOPE_REQUIRED_MESSAGE
from app.services.costing.assembly_cost.calc.orchestrator.deps import AssemblyCalcDeps
from app.services.costing.assembly_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.assembly_cost.calc.orchestrator.ready import assert_calc_ready
from app.services.costing.assembly_cost.calc.process_log import (
    CONFLICT_LIMIT,
    ProcessLogBuilder,
)
from app.services.costing.assembly_cost.calc.rollup import (
    RollupBomNode,
    RollupFinishedRates,
    RollupPackagingFee,
    RollupWeldingFee,
)
from app.services.costing.assembly_cost.calc.seq_label import calc_card_seq_labels
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService


@dataclass(frozen=True, slots=True)
class SubjectMeta:
    procurement_object_id: int | None = None
    object_kind: str | None = None


@dataclass(slots=True)
class CalcPrepContext:
    year: int
    month: int
    location: str
    vehicle_model: str
    children: dict[int | None, list[RollupBomNode]]
    nodes_by_id: dict[int, RollupBomNode]
    subjects: list[RollupBomNode]
    subject_meta: dict[int, SubjectMeta]
    stamping_prices: dict[str, Decimal]
    conflicted_part_numbers: frozenset[str]
    annual_prices: dict[str, Decimal]
    annual_suppliers: dict[str, str]
    welding_by_bom_node: dict[int, RollupWeldingFee]
    packaging_by_part: dict[str, RollupPackagingFee]
    rates: RollupFinishedRates
    procurement_missing: bool
    seq_label_by_node_id: dict[int, str]
    log_builder: ProcessLogBuilder


def _build_stamping_price_maps(
    rows: list[StampingPartCost],
) -> tuple[dict[str, Decimal], frozenset[str]]:
    grouped: dict[str, set[Decimal]] = defaultdict(set)
    first: dict[str, Decimal] = {}
    for row in rows:
        if row.unit_cost is None:
            continue
        amount = Decimal(str(row.unit_cost))
        grouped[row.part_number].add(amount)
        first.setdefault(row.part_number, amount)
    prices: dict[str, Decimal] = {}
    conflicted: set[str] = set()
    for part_number, amounts in grouped.items():
        if len(amounts) > 1:
            conflicted.add(part_number)
            continue
        prices[part_number] = first[part_number]
    return prices, frozenset(conflicted)


def prepare_calc_run(
    db: Session,
    deps: AssemblyCalcDeps,
    dto: AssemblyCostCalcDTO,
    progress: ProgressNotifier,
) -> CalcPrepContext:
    year = dto.year
    month = dto.month
    location = dto.location.strip()
    vehicle_model = dto.vehicle_model.strip()
    if not location or not vehicle_model:
        raise BusinessException(SCOPE_REQUIRED_MESSAGE)
    location, vehicle_model = VehicleModelService().require_introducible(
        db, location, vehicle_model, year, month
    )

    assert_calc_ready(
        db,
        deps,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
    )

    progress.report(5, "加载 BOM…")
    orm_nodes = BomPeriodService().list_as_of_trees(
        db,
        location=location,
        vehicle_model=vehicle_model,
        as_of_year=year,
        as_of_month=month,
    )
    if not orm_nodes:
        raise BusinessException(
            f"{location}/{vehicle_model} 在 {year} 年 {month:02d} 月没有有效期内的 BOM 树"
        )

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
            seq_no=n.seq_no,
            excel_row=n.excel_row,
            supply_type=getattr(n, "supply_type", None),
            sketch_url=getattr(n, "sketch_url", None),
            snapshot_id=n.snapshot_id,
            bom_version=(n.bom_version or "").strip(),
        )
        for n in orm_nodes
    ]
    nodes_by_id = {n.id: n for n in nodes}
    children: dict[int | None, list[RollupBomNode]] = {}
    for node in nodes:
        children.setdefault(node.parent_id, []).append(node)

    parent_ids = {n.parent_id for n in nodes if n.parent_id is not None}
    set_a = {n.id for n in nodes if n.id in parent_ids}
    set_b = {n.id for n in nodes if n.parent_id is None}

    procurement_repo = BomProcurementObjectRepository()
    headers = procurement_repo.list_lists_by_location_vehicle(
        db, location=location, vehicle_model=vehicle_model
    )
    procurement_objects = [
        obj
        for header in headers
        for obj in procurement_repo.list_objects_by_list_id(db, header.id)
        if obj.source_node_id is not None and int(obj.source_node_id) in nodes_by_id
    ]
    subject_meta: dict[int, SubjectMeta] = {}
    set_c: set[int] = set()
    for obj in procurement_objects:
        if obj.section != SECTION_OBJECT:
            continue
        set_c.add(obj.source_node_id)
        subject_meta[obj.source_node_id] = SubjectMeta(
            procurement_object_id=obj.id,
            object_kind=obj.object_kind,
        )
    procurement_missing = not headers

    subject_ids = set_a | set_b | set_c
    if dto.levels:
        allowed = set(dto.levels)
        subject_ids = {
            nid for nid in subject_ids if nodes_by_id.get(nid) and nodes_by_id[nid].level in allowed
        }
    subjects = sorted(
        [nodes_by_id[nid] for nid in subject_ids if nid in nodes_by_id],
        key=bom_node_order_from,
    )
    if not subjects:
        raise BusinessException("无核价主体（装配∪树根∪采购对象）")
    seq_label_by_node_id = calc_card_seq_labels(
        orm_nodes,
        procurement_objects,
        {node.id for node in subjects},
    )

    progress.report(15, "加载上游价表…")
    stamping_prices, conflicted = _build_stamping_price_maps(
        deps.stamping_cost_repo.list_calc_success_with_unit_cost(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
        )
    )
    annual_prices: dict[str, Decimal] = {}
    annual_suppliers: dict[str, str] = {}
    for row in deps.annual_price_repo.list_with_unit_price(db, location=location, year=year):
        annual_prices[row.part_number] = Decimal(str(row.unit_price))
        name = getattr(row, "supplier_name", None)
        if name:
            annual_suppliers[row.part_number] = str(name)

    current_ids = {int(node.id) for node in nodes}
    breakdowns = BomWeldingProcessBreakdownRepository().list_by_source_node_ids(
        db, list(current_ids)
    )
    fee_by_breakdown_id: dict[int, RollupWeldingFee] = {}
    for weld_row in deps.welding_fee_repo.list_by_calc_scope(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        source_node_ids=current_ids,
        level=None,
    ):
        breakdown_id = weld_row.source_breakdown_node_id
        if breakdown_id is None:
            continue
        final = weld_row.final_welding_fee
        if final is None:
            final = weld_row.total_welding_fee or Decimal("0")
        fee_by_breakdown_id[breakdown_id] = RollupWeldingFee(
            final_amount=Decimal(str(final)),
            other_fee=Decimal(str(weld_row.other_fee or 0)),
            missing_price_count=int(weld_row.missing_price_count or 0),
            welding_fee_id=weld_row.id,
            summary=None,
            calc_status=weld_row.calc_status,
        )
    welding_by_bom_node: dict[int, RollupWeldingFee] = {}
    for bd in breakdowns:
        if bd.source_node_id is None:
            continue
        fee = fee_by_breakdown_id.get(bd.id)
        if fee is not None:
            welding_by_bom_node[int(bd.source_node_id)] = fee

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
    log_builder = ProcessLogBuilder()
    _record_prep(
        log_builder,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        node_count=len(nodes),
        subjects=subjects,
        procurement_missing=procurement_missing,
        stamping_count=len(stamping_prices),
        conflicted=conflicted,
        annual_count=len(annual_prices),
        welding_count=len(welding_by_bom_node),
        packaging_count=len(packaging_by_part),
    )
    return CalcPrepContext(
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        children=children,
        nodes_by_id=nodes_by_id,
        subjects=subjects,
        subject_meta=subject_meta,
        stamping_prices=stamping_prices,
        conflicted_part_numbers=conflicted,
        annual_prices=annual_prices,
        annual_suppliers=annual_suppliers,
        welding_by_bom_node=welding_by_bom_node,
        packaging_by_part=packaging_by_part,
        rates=rates,
        procurement_missing=procurement_missing,
        seq_label_by_node_id=seq_label_by_node_id,
        log_builder=log_builder,
    )


def _record_prep(
    log_builder: ProcessLogBuilder,
    *,
    year: int,
    month: int,
    location: str,
    vehicle_model: str,
    node_count: int,
    subjects: list[RollupBomNode],
    procurement_missing: bool,
    stamping_count: int,
    conflicted: frozenset[str],
    annual_count: int,
    welding_count: int,
    packaging_count: int,
) -> None:
    by_level = Counter(node.level for node in subjects)
    level_text = "、".join(f"L{level} {count}" for level, count in sorted(by_level.items()))
    log_builder.line(
        f"{year}-{month:02d}  {location}/{vehicle_model}  "
        f"BOM {node_count}  卡 {len(subjects)}（{level_text or '无'}）"
    )
    log_builder.line(
        f"冲压价 {stamping_count}  年度价 {annual_count}  "
        f"焊接费 {welding_count}  包装 {packaging_count}"
    )
    if procurement_missing:
        log_builder.line("本趟无采购对象清单头（应列入为空时正常）")
    if conflicted:
        shown = sorted(conflicted)[:CONFLICT_LIMIT]
        extra = f" 等{len(conflicted)}个" if len(conflicted) > len(shown) else ""
        log_builder.warn("冲压价冲突: " + "、".join(shown) + extra)
    elif stamping_count == 0:
        log_builder.warn("本月无冲压价")
