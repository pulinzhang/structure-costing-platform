"""总成核价就绪统计与 P20 硬门。"""

from __future__ import annotations

from collections import defaultdict
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.bom.welding_fee_calc_log_repository import BomWeldingFeeCalcLogRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_calc_log_repository import (
    StampingPartCostCalcLogRepository,
)
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.schemas.vo.assembly_cost_vo import AssemblyCostCalcReadyVO
from app.services.bom.procurement_object.classify import SECTION_OBJECT
from app.services.costing.assembly_cost.calc.orchestrator.deps import AssemblyCalcDeps
from app.services.costing.stamping_part_cost.calc.constants import ALL_SUPPLIERS_LOCK


class WeldingCoverage(NamedTuple):
    complete: bool
    message: str
    fee_count: int
    level_counts: dict[int, int]


def collect_calc_ready(
    db: Session,
    deps: AssemblyCalcDeps,
    *,
    year: int,
    month: int,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> AssemblyCostCalcReadyVO:
    location = location.strip()
    vehicle_model = vehicle_model.strip()
    bom_version = bom_version.strip()
    snap = deps.bom_snapshot_repo.get_by_unique_key(db, location, vehicle_model, bom_version)

    tree_root_count = 0
    subject_count = 0
    weld_info_count = 0
    orm_nodes = []
    if snap is not None:
        orm_nodes = deps.bom_node_repo.list_by_snapshot(db, snap.id)
        parent_ids = {n.parent_id for n in orm_nodes if n.parent_id is not None}
        set_a = {n.id for n in orm_nodes if n.id in parent_ids}
        set_b = {n.id for n in orm_nodes if n.parent_id is None}
        tree_root_count = len(set_b)
        weld_info_count = sum(1 for n in orm_nodes if (n.weld_info or "").strip())
        header = BomProcurementObjectRepository().get_list_by_scope(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )
        set_c: set[int] = set()
        procurement_object_count = 0
        if header is not None:
            objects = BomProcurementObjectRepository().list_objects_by_list_id(db, header.id)
            for obj in objects:
                if obj.section == SECTION_OBJECT and obj.source_node_id is not None:
                    set_c.add(int(obj.source_node_id))
            procurement_object_count = len(set_c)
        subject_count = len(set_a | set_b | set_c)
    else:
        procurement_object_count = 0
    current_ids = {int(n.id) for n in orm_nodes}

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
        deps,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        current_ids=current_ids,
        weld_info_count=weld_info_count,
    )

    ready = True
    message = None
    if snap is None:
        ready = False
        message = "未找到对应 BOM 快照"
    elif subject_count == 0:
        ready = False
        message = "无核价主体（装配∪树根）"
    elif not stamping_ok:
        ready = False
        message = stamping_message
    elif not welding.complete:
        ready = False
        message = welding.message
    elif procurement_object_count == 0:
        message = "采购对象未生成，本趟只出装配∪树根"

    return AssemblyCostCalcReadyVO(
        l0_count=tree_root_count,
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
        bom_version=bom_version,
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
    bom_version: str,
) -> AssemblyCostCalcReadyVO:
    vo = collect_calc_ready(
        db,
        deps,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
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
        db, location=location, vehicle_model=vehicle_model
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
    deps: AssemblyCalcDeps,
    *,
    year: int,
    location: str,
    vehicle_model: str,
    bom_version: str,
    current_ids: set[int],
    weld_info_count: int,
) -> WeldingCoverage:
    breakdowns = BomWeldingProcessBreakdownRepository().list_by_scope(
        db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
    )
    live_breakdowns = [
        bd
        for bd in breakdowns
        if bd.source_node_id is not None and int(bd.source_node_id) in current_ids
    ]
    live_breakdown_ids = {int(bd.id) for bd in live_breakdowns}
    fees = deps.welding_fee_repo.list_by_calc_scope(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
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

    latest = BomWeldingFeeCalcLogRepository().get_latest(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
    )
    if latest is None:
        return WeldingCoverage(
            False, "从未算过焊接费，请先到焊接费计算页完成", fee_count, level_counts
        )
    if latest.status in {"processing", "failed"}:
        return WeldingCoverage(
            False,
            f"焊接费最新日志为 {latest.status}，请先完成焊接费计算",
            fee_count,
            level_counts,
        )
    if weld_info_count > 0 and len(breakdowns) < weld_info_count:
        return WeldingCoverage(
            False,
            "有焊信的节点尚未全部进入拆解，请先生成焊接工艺拆解",
            fee_count,
            level_counts,
        )
    if len(live_breakdowns) != len(breakdowns):
        return WeldingCoverage(
            False,
            f"焊接拆解/费行未对齐当前 BOM 树（当前树对齐 {fee_count} 条），请重导后重算焊接费",
            fee_count,
            level_counts,
        )
    if any(bd.id not in covered_ids for bd in live_breakdowns):
        return WeldingCoverage(
            False,
            (
                f"拆解节点没有对应的焊接费行"
                f"（当前树拆解 {len(live_breakdowns)} 条，对齐 {fee_count} 条），"
                "请先完成焊接费计算"
            ),
            fee_count,
            level_counts,
        )
    return WeldingCoverage(True, "焊接费已完成", fee_count, level_counts)
