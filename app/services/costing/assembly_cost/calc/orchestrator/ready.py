"""总成核价就绪统计与 P20 硬门。"""

from __future__ import annotations

from collections import defaultdict
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.bom.welding_fee_calc_log_repository import BomWeldingFeeCalcLogRepository
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_calc_log_repository import (
    StampingPartCostCalcLogRepository,
)
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.vo.assembly_cost_vo import AssemblyCostCalcReadyVO
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.procurement_object.classify import SECTION_OBJECT, classify_nodes
from app.services.costing.assembly_cost.calc.orchestrator.deps import AssemblyCalcDeps
from app.services.costing.stamping_part_cost.calc.constants import ALL_SUPPLIERS_LOCK
from app.services.masterdata.vehicle_model.service import VehicleModelService


class WeldingCoverage(NamedTuple):
    complete: bool
    message: str
    fee_count: int
    level_counts: dict[int, int]
    breakdown_complete: bool = True


def evaluate_welding_coverage(
    db: Session,
    *,
    year: int,
    location: str,
    vehicle_model: str,
    welding_fee_repo: BomWeldingFeeRepository | None = None,
) -> WeldingCoverage:
    """该年有效期内树上拆解是否齐、拆解节点是否都有焊接费行。

    年 + 基地 + 项目；年交集只问 L0 树根再收子树。不认 snapshot 头字。
    """
    period_nodes = BomPeriodService().list_year_overlap_trees(
        db, location=location, vehicle_model=vehicle_model, year=year
    )
    current_ids = {int(n.id) for n in period_nodes}
    weld_info_count = sum(1 for n in period_nodes if (n.weld_info or "").strip())
    return _welding_coverage(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        current_ids=current_ids,
        weld_info_count=weld_info_count,
        welding_fee_repo=welding_fee_repo,
    )


def collect_calc_ready(
    db: Session,
    deps: AssemblyCalcDeps,
    *,
    year: int,
    month: int,
    location: str,
    vehicle_model: str,
) -> AssemblyCostCalcReadyVO:
    location = location.strip()
    vehicle_model = vehicle_model.strip()
    try:
        location, vehicle_model = VehicleModelService().require_introducible(
            db, location, vehicle_model, year, month
        )
    except BusinessException as exc:
        return AssemblyCostCalcReadyVO(
            tree_root_count=0,
            subject_count=0,
            procurement_object_count=0,
            stamping_price_count=0,
            annual_price_count=0,
            welding_fee_count=0,
            packaging_fee_count=0,
            ready=False,
            message=str(exc),
        )
    orm_nodes = BomPeriodService().list_as_of_trees(
        db,
        location=location,
        vehicle_model=vehicle_model,
        as_of_year=year,
        as_of_month=month,
    )
    parent_ids = {n.parent_id for n in orm_nodes if n.parent_id is not None}
    set_a = {n.id for n in orm_nodes if n.id in parent_ids}
    set_b = {n.id for n in orm_nodes if n.parent_id is None}
    tree_root_count = len(set_b)
    weld_info_count = sum(1 for n in orm_nodes if (n.weld_info or "").strip())
    current_ids = {int(n.id) for n in orm_nodes}

    objects = BomProcurementObjectRepository().list_objects_by_location_vehicle(
        db, location=location, vehicle_model=vehicle_model
    )
    set_c: set[int] = set()
    for obj in objects:
        if obj.section == SECTION_OBJECT and obj.source_node_id is not None:
            node_id = int(obj.source_node_id)
            if node_id in current_ids:
                set_c.add(node_id)
    procurement_object_count = len(set_c)
    subject_count = len(set_a | set_b | set_c)

    stamping_n = deps.stamping_cost_repo.count_calc_success_with_unit_cost(
        db,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
    )
    annual_n = deps.annual_price_repo.count_with_unit_price(db, location=location, year=year)
    pkg_n = deps.packaging_fee_repo.count_by_location_year(db, location=location, year=year)

    stamping_ok, incomplete_suppliers, stamping_message = _stamping_complete(
        db, year=year, month=month, location=location, vehicle_model=vehicle_model
    )
    welding = _welding_coverage(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        current_ids=current_ids,
        weld_info_count=weld_info_count,
        welding_fee_repo=deps.welding_fee_repo,
    )

    ready = True
    message = None
    if not orm_nodes:
        ready = False
        message = f"{location}/{vehicle_model} 在 {year} 年 {month:02d} 月没有有效期内的 BOM 树"
    elif subject_count == 0:
        ready = False
        message = "无核价主体（装配∪树根）"
    elif not stamping_ok:
        ready = False
        message = stamping_message
    elif not welding.complete:
        ready = False
        message = welding.message
    else:
        expected_ids = {
            int(row.source_node_id)
            for row in classify_nodes(orm_nodes).rows
            if row.section == SECTION_OBJECT
        }
        if expected_ids and not expected_ids.issubset(set_c):
            ready = False
            missing_n = len(expected_ids - set_c)
            message = (
                "请先生成采购对象清单"
                if not set_c
                else f"采购对象未齐（缺 {missing_n}），请重新生成"
            )

    return AssemblyCostCalcReadyVO(
        tree_root_count=tree_root_count,
        subject_count=subject_count,
        procurement_object_count=procurement_object_count,
        stamping_price_count=stamping_n,
        annual_price_count=annual_n,
        welding_fee_count=welding.fee_count,
        welding_fee_level_counts=welding.level_counts,
        packaging_fee_count=pkg_n,
        stamping_complete=stamping_ok,
        stamping_incomplete_suppliers=incomplete_suppliers,
        welding_calc_complete=welding.complete,
        bom_version=None,
        ready=ready,
        message=message,
    )


def assert_calc_ready(
    db: Session,
    deps: AssemblyCalcDeps,
    *,
    year: int,
    month: int,
    location: str,
    vehicle_model: str,
) -> AssemblyCostCalcReadyVO:
    vo = collect_calc_ready(
        db,
        deps,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
    )
    if not vo.ready:
        raise BusinessException(vo.message or "上游计算未完成，不能开始总成核价")
    return vo


def _stamping_complete(
    db: Session,
    *,
    year: int,
    month: int,
    location: str,
    vehicle_model: str,
) -> tuple[bool, list[str], str]:
    parts = StampingPartRepository().list_by_location_and_vehicle(
        db,
        location=location,
        vehicle_model=vehicle_model,
        as_of_year=year,
        as_of_month=month,
    )
    by_supplier: dict[str, set[str]] = defaultdict(set)
    for part in parts:
        supplier = (part.stamping_supplier or "").strip()
        if not supplier or not part.part_number:
            continue
        by_supplier[supplier].add(part.part_number)
    if not by_supplier:
        return True, [], "无冲压工艺，跳过零件价完成检查"

    from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
        StampingPartCostRepository,
    )

    success_rows = StampingPartCostRepository().list_calc_success_with_unit_cost(
        db, year=year, month=month, location=location, vehicle_model=vehicle_model
    )
    success_numbers = {row.part_number for row in success_rows if row.part_number}
    success_by_supplier: dict[str, set[str]] = defaultdict(set)
    for row in success_rows:
        supplier = (getattr(row, "stamping_supplier", None) or "").strip()
        if supplier and row.part_number:
            success_by_supplier[supplier].add(row.part_number)

    log_repo = StampingPartCostCalcLogRepository()
    latest = log_repo.get_latest(
        db,
        year=year,
        month=month,
        location=location,
        stamping_supplier=ALL_SUPPLIERS_LOCK,
        vehicle_model=vehicle_model,
    )
    if latest is not None and latest.status in {"processing", "failed"}:
        return (
            False,
            [],
            "冲压零件价整车计算未完成（进行中或失败），请先到零件核价页算完",
        )

    expected_numbers = set()
    for numbers in by_supplier.values():
        expected_numbers |= numbers
    if not expected_numbers.issubset(success_numbers):
        incomplete = [
            supplier
            for supplier, numbers in sorted(by_supplier.items())
            if not numbers.issubset(success_by_supplier.get(supplier, set()))
        ]
        names = "、".join(incomplete) if incomplete else "—"
        return (
            False,
            incomplete,
            f"冲压零件价未完成（缺件工厂：{names}），请先到零件核价页算完",
        )
    return True, [], "零件价已完成"


def _welding_coverage(
    db: Session,
    *,
    year: int,
    location: str,
    vehicle_model: str,
    current_ids: set[int],
    weld_info_count: int,
    welding_fee_repo: BomWeldingFeeRepository | None = None,
) -> WeldingCoverage:
    fee_repo = welding_fee_repo or BomWeldingFeeRepository()
    breakdowns = BomWeldingProcessBreakdownRepository().list_by_source_node_ids(
        db, list(current_ids)
    )
    live_breakdown_ids = {int(bd.id) for bd in breakdowns}
    fees = fee_repo.list_by_calc_scope(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        level=None,
    )
    aligned_fees = [
        fee
        for fee in fees
        if fee.source_breakdown_node_id is not None
        and int(fee.source_breakdown_node_id) in live_breakdown_ids
    ]
    level_counts: dict[int, int] = {}
    for fee in aligned_fees:
        lvl = int(fee.level or 0)
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
    fee_count = len(aligned_fees)
    covered_ids = {
        int(breakdown_id)
        for fee in aligned_fees
        if (breakdown_id := fee.source_breakdown_node_id) is not None
    }
    missing_weld_info = weld_info_count > 0 and len(breakdowns) < weld_info_count
    breakdown_complete = bool(breakdowns) and not missing_weld_info

    latest = BomWeldingFeeCalcLogRepository().get_latest(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
    )
    if latest is None:
        return WeldingCoverage(
            False,
            "从未算过焊接费，请先到焊接费计算页完成",
            fee_count,
            level_counts,
            breakdown_complete,
        )
    if latest.status in {"processing", "failed"}:
        return WeldingCoverage(
            False,
            f"焊接费最新日志为 {latest.status}，请先完成焊接费计算",
            fee_count,
            level_counts,
            breakdown_complete,
        )
    if missing_weld_info:
        return WeldingCoverage(
            False,
            "有焊信的节点尚未全部进入拆解，请先生成焊接工艺拆解",
            fee_count,
            level_counts,
            False,
        )
    if any(bd.id not in covered_ids for bd in breakdowns):
        return WeldingCoverage(
            False,
            (
                f"拆解节点没有对应的焊接费行"
                f"（当前树拆解 {len(breakdowns)} 条，对齐 {fee_count} 条），"
                "请先完成焊接费计算"
            ),
            fee_count,
            level_counts,
            True,
        )
    return WeldingCoverage(True, "焊接费已完成", fee_count, level_counts, True)
