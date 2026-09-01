"""芜湖 T13J 2026-01 总成核价：P20 开算后全量重算，并对照设计硬门（97 张卡）。

在仓库根目录执行::

    python -X utf8 -m scripts.run_t13j_2026_01_assembly_recalc
"""

from __future__ import annotations

import logging
from collections import Counter
from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.common.audit import SYSTEM_USER
from app.common.money import Q4
from app.database import DatabaseConfig
from app.models.bom import BomAnnualPartPrice, BomNode, BomSnapshot, BomWeldingFee
from app.models.costing import AssemblyCost
from app.schemas.dto.assembly_cost_dto import AssemblyCostCalcDTO
from app.services.costing.assembly_cost.calc.orchestrator import (
    AssemblyCostCalcOrchestrator,
)
from app.services.costing.assembly_cost.calc.rollup import FORMULA_VERSION

YEAR = 2026
MONTH = 1
LOCATION = "芜湖"
VEHICLE = "T13J"
BOM_VERSION = "D/09"
EXPECTED_SUBJECTS_NO_LIST = 97
EXPECTED_SUBJECTS_WITH_LIST = 229
EXPECTED_TREE_ROOTS = 44
EXPECTED_DEGENERATE_ROOTS = 14
EXPECTED_SUBASSEMBLY_CARDS = 53
EXPECTED_L1_WELD_ROWS = 53
EXPECTED_ANNUAL = 7

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


def _d(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Q4)


def _scope_cards(db: Session) -> list[AssemblyCost]:
    return (
        db.query(AssemblyCost)
        .options(selectinload(AssemblyCost.items))
        .filter(
            AssemblyCost.year == YEAR,
            AssemblyCost.month == MONTH,
            AssemblyCost.location == LOCATION,
            AssemblyCost.vehicle_model == VEHICLE,
            AssemblyCost.bom_version == BOM_VERSION,
        )
        .all()
    )


def _assert_hard_gates(
    db: Session,
    snap: BomSnapshot,
    *,
    expected_cards: int,
    errors: list[str],
) -> None:
    nodes = db.query(BomNode).filter(BomNode.snapshot_id == snap.id).all()
    parent_ids = {n.parent_id for n in nodes if n.parent_id is not None}
    tree_roots = [n for n in nodes if n.parent_id is None]
    degenerate_ids = {n.id for n in tree_roots if n.id not in parent_ids}
    subassembly_ids = {n.id for n in nodes if n.id in parent_ids and n.parent_id is not None}

    if len(nodes) != 357:
        errors.append(f"BOM 节点数 {len(nodes)}，期望 357")
    if len(tree_roots) != EXPECTED_TREE_ROOTS:
        errors.append(f"树根 {len(tree_roots)}，期望 {EXPECTED_TREE_ROOTS}")
    if len(degenerate_ids) != EXPECTED_DEGENERATE_ROOTS:
        errors.append(f"退化树根 {len(degenerate_ids)}，期望 {EXPECTED_DEGENERATE_ROOTS}")

    cards = _scope_cards(db)
    if len(cards) != expected_cards:
        errors.append(f"落库卡数 {len(cards)}，期望 {expected_cards}")

    finance = [c for c in cards if c.is_tree_root]
    if len(finance) != EXPECTED_TREE_ROOTS:
        errors.append(f"财务树根卡 {len(finance)}，期望 {EXPECTED_TREE_ROOTS}")

    sub_cards = [c for c in cards if c.source_node_id in subassembly_ids]
    if len(sub_cards) != EXPECTED_SUBASSEMBLY_CARDS:
        errors.append(f"分总成卡 {len(sub_cards)}，期望 {EXPECTED_SUBASSEMBLY_CARDS}")

    deg_cards = [c for c in cards if c.source_node_id in degenerate_ids]
    if len(deg_cards) != EXPECTED_DEGENERATE_ROOTS:
        errors.append(f"退化树根卡 {len(deg_cards)}，期望 {EXPECTED_DEGENERATE_ROOTS}")
    for card in deg_cards:
        if _d(card.material_amount) <= 0:
            errors.append(
                f"退化树根 {card.part_number} 材料为 {_d(card.material_amount)}（P5 应作叶子，材料非 0）"
            )

    weld_l1 = (
        db.query(BomWeldingFee)
        .filter(
            BomWeldingFee.year == YEAR,
            BomWeldingFee.location == LOCATION,
            BomWeldingFee.vehicle_model == VEHICLE,
            BomWeldingFee.bom_version == BOM_VERSION,
            BomWeldingFee.level == 1,
        )
        .count()
    )
    if weld_l1 != EXPECTED_L1_WELD_ROWS:
        errors.append(f"L1 焊接费行 {weld_l1}，期望 {EXPECTED_L1_WELD_ROWS}")
    if len(sub_cards) == EXPECTED_SUBASSEMBLY_CARDS and weld_l1 == EXPECTED_L1_WELD_ROWS:
        print(f"分总成卡 {len(sub_cards)} 对 L1 焊接费 {weld_l1}")

    annual_rows = (
        db.query(BomAnnualPartPrice)
        .filter(
            BomAnnualPartPrice.location == LOCATION,
            BomAnnualPartPrice.year == YEAR,
        )
        .all()
    )
    if len(annual_rows) != EXPECTED_ANNUAL:
        errors.append(f"年度价 {len(annual_rows)} 条，期望 {EXPECTED_ANNUAL}")
    annual_numbers = {(row.part_number or "").strip() for row in annual_rows}
    nodes_with_children = {n.part_number for n in nodes if n.id in parent_ids}
    annual_on_parents = annual_numbers & nodes_with_children
    if annual_on_parents:
        errors.append(f"年度价落在有子件节点（应只测叶子）: {sorted(annual_on_parents)}")

    bundle_n = 0
    skipped_n = 0
    identity_fail = 0
    pkg_nonzero = 0
    formula_bad = 0
    status_counts: Counter[str] = Counter()
    for card in cards:
        status_counts[card.calc_status] += 1
        if card.formula_version != FORMULA_VERSION:
            formula_bad += 1
        if _d(card.unit_transport_fee) != 0 or _d(card.warehouse_bundling_fee) != 0:
            pkg_nonzero += 1
        material = _d(card.stamping_amount) + _d(card.purchased_amount) + _d(card.bundle_amount)
        if material != _d(card.material_amount):
            identity_fail += 1
        total = _d(card.material_amount) + _d(card.welding_amount) + _d(card.welding_other_fee)
        if total != _d(card.total_amount) or _d(card.should_cost) != _d(card.total_amount):
            identity_fail += 1
        if _d(card.grand_total) != _d(card.total_amount) + _d(card.indirect_amount):
            identity_fail += 1
        for item in card.items:
            if item.cost_source == "bundle":
                bundle_n += 1
            elif item.cost_source == "skipped_by_bundle":
                skipped_n += 1

    print(
        f"核算状态 {dict(status_counts)} formula_bad={formula_bad} "
        f"identity_fail={identity_fail} 一口价行={bundle_n} 剪枝行={skipped_n} 包装非0卡={pkg_nonzero}"
    )
    if formula_bad:
        errors.append(f"{formula_bad} 张卡 formula_version 不是 {FORMULA_VERSION}")
    if identity_fail:
        errors.append(f"{identity_fail} 张卡恒等式失败")
    if bundle_n or skipped_n:
        errors.append(f"出现一口价/剪枝明细 bundle={bundle_n} skipped={skipped_n}（T13J 不应有）")
    if pkg_nonzero:
        errors.append(f"{pkg_nonzero} 张卡 I1/I2 非 0（包装应为 0）")


def main() -> int:
    from app import models as _models  # noqa: F401

    DatabaseConfig.create_tables()
    DatabaseConfig.get_engine().echo = False
    factory = DatabaseConfig.get_session_factory()
    db = factory()
    errors: list[str] = []
    try:
        snap = (
            db.query(BomSnapshot)
            .filter(
                BomSnapshot.location == LOCATION,
                BomSnapshot.vehicle_model == VEHICLE,
                BomSnapshot.bom_version == BOM_VERSION,
            )
            .first()
        )
        print(f"=== {LOCATION} {VEHICLE} {YEAR}-{MONTH:02d} BOM {BOM_VERSION} 总成核价 ===")
        if snap is None:
            print("未找到 BOM 快照")
            return 1
        print(f"snapshot_id={snap.id}")

        orch = AssemblyCostCalcOrchestrator()
        ready = orch.get_calc_ready(
            db,
            year=YEAR,
            month=MONTH,
            location=LOCATION,
            vehicle_model=VEHICLE,
            bom_version=BOM_VERSION,
        )
        print(
            f"ready={ready.ready} message={ready.message}\n"
            f"  树根={ready.tree_root_count} 主体={ready.subject_count} "
            f"清单对象={ready.procurement_object_count}\n"
            f"  冲压价={ready.stamping_price_count} 冲压完成={ready.stamping_complete} "
            f"未完成厂={ready.stamping_incomplete_suppliers}\n"
            f"  焊接费={ready.welding_fee_count} 分层={ready.welding_fee_level_counts} "
            f"焊接完成={ready.welding_calc_complete}\n"
            f"  年度价={ready.annual_price_count} 包装={ready.packaging_fee_count}"
        )
        if not ready.ready:
            print("P20 未通过，不开始计算")
            return 1
        if ready.procurement_object_count == 0:
            expected_cards = EXPECTED_SUBJECTS_NO_LIST
        else:
            expected_cards = EXPECTED_SUBJECTS_WITH_LIST
            print(
                f"清单已生成（对象 {ready.procurement_object_count}），"
                f"本趟按设计验收 {expected_cards} 张卡"
            )
        if ready.subject_count != expected_cards:
            errors.append(f"主体 {ready.subject_count}，期望 {expected_cards}")

        dto = AssemblyCostCalcDTO(
            year=YEAR,
            month=MONTH,
            location=LOCATION,
            vehicle_model=VEHICLE,
            bom_version=BOM_VERSION,
        )
        print("\n=== 开始计算 ===")
        result = orch.calculate(db, dto, current_user=SYSTEM_USER)
        print(
            f"status={result.status} created={result.created_count} "
            f"updated={result.updated_count} skipped_approved={result.skipped_approved_count} "
            f"ok={result.ok_count} partial={result.partial_count} failed={result.failed_count}\n"
            f"{result.message}"
        )
        if result.status == "failed" or result.failed_count:
            errors.append(f"计算失败 status={result.status} failed={result.failed_count}")
        if result.skipped_approved_count:
            errors.append(f"跳过已审 {result.skipped_approved_count}，无法对照全量 97 张")

        db.expire_all()
        print("\n=== 硬门对照 ===")
        _assert_hard_gates(db, snap, expected_cards=expected_cards, errors=errors)

        if errors:
            print("\n测试未通过:")
            for item in errors:
                print(f"  - {item}")
            return 1
        print(
            f"\n测试通过：P20 可开算，{expected_cards} 张卡，"
            "分总成/退化根/年度价叶子/包装 0/恒等式"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
