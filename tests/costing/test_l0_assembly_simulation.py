"""
成品 L0 月核价模拟测试

- 单元：内存小树，锁定取价 / rollup / 一口价规则
- 集成：青岛 T28 · 2025-01 现网数据全量走一遍
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.models.bom.annual_part_price import BomAnnualPartPrice
from app.models.bom.l0_welding_fee import BomL0WeldingFee
from app.models.bom.node import BomNode, BomSnapshot
from app.models.costing.stamping_part_cost import StampingPartCost
from tests.costing.l0_assembly_sim import (
    L0SimResult,
    SimBomNode,
    SimWeldingFee,
    format_simulation_report,
    quantize_money,
    simulate_all_l0,
    simulate_l0,
)

_REPORT_PATH = Path(__file__).resolve().parent / "last_qingdao_t28_sim_report.txt"

LOCATION = "青岛"
VEHICLE_MODEL = "T28"
YEAR = 2025
MONTH = 1


# ---------------------------------------------------------------------------
# 单元：规则锁定
# ---------------------------------------------------------------------------


def test_l1_leaf_stamping_then_annual_fallback() -> None:
    """无子件 L1：先完整零件号对冲压价，没有再对年度价。"""
    l0 = SimBomNode(
        id=1,
        parent_id=None,
        level=0,
        part_number="L0-1",
        part_name="成品",
        qty=Decimal("1"),
        node_role="supply",
    )
    l1_stamp = SimBomNode(
        id=2,
        parent_id=1,
        level=1,
        part_number="P-STAMP",
        part_name="冲压叶子",
        qty=Decimal("2"),
        node_role="make",
        sort_no=1,
    )
    l1_annual = SimBomNode(
        id=3,
        parent_id=1,
        level=1,
        part_number="P-BUY",
        part_name="外购叶子",
        qty=Decimal("3"),
        node_role="buy",
        sort_no=2,
    )
    children = {None: [l0], 1: [l1_stamp, l1_annual]}
    result = simulate_l0(
        l0=l0,
        children_by_parent=children,
        stamping_prices={"P-STAMP": Decimal("1.2500")},
        annual_prices={"P-BUY": Decimal("0.1000")},
        welding=SimWeldingFee(final_amount=Decimal("0.5000")),
    )
    assert result.status == "ok"
    assert result.stamping_amount == Decimal("2.5000")  # 1.25 × 2
    assert result.purchased_amount == Decimal("0.3000")  # 0.10 × 3
    assert result.welding_amount == Decimal("0.5000")
    assert result.total_amount == Decimal("3.3000")


def test_dash_suffix_falls_back_to_stamping_base_part_number() -> None:
    """完整号找不到时：取「-」前零件号，仅回退冲压价。"""
    l0 = SimBomNode(
        id=1,
        parent_id=None,
        level=0,
        part_number="551001730AA",
        part_name="成品",
        qty=Decimal("1"),
        node_role="supply",
    )
    l1 = SimBomNode(
        id=2,
        parent_id=1,
        level=1,
        part_number="551001730AA-1",
        part_name="板料",
        qty=Decimal("1"),
        node_role="make",
    )
    result = simulate_l0(
        l0=l0,
        children_by_parent={1: [l1]},
        stamping_prices={"551001730AA": Decimal("28.6623")},  # 仅「-」前有价
        annual_prices={},
        welding=SimWeldingFee(final_amount=Decimal("0.4680")),
    )
    assert result.status == "ok"
    assert result.stamping_amount == Decimal("28.6623")
    assert result.welding_amount == Decimal("0.4680")
    assert result.total_amount == Decimal("29.1303")
    assert not result.missing


def test_dash_suffix_does_not_fall_back_to_annual_base() -> None:
    """「-」前回退只查冲压价，不查年度价。"""
    l0 = SimBomNode(
        id=1, parent_id=None, level=0, part_number="L0", part_name="A",
        qty=Decimal("1"), node_role="supply",
    )
    l1 = SimBomNode(
        id=2, parent_id=1, level=1, part_number="P-1", part_name="叶子",
        qty=Decimal("1"), node_role="make",
    )
    result = simulate_l0(
        l0=l0,
        children_by_parent={1: [l1]},
        stamping_prices={},
        annual_prices={"P": Decimal("9.9900")},
        welding=SimWeldingFee(final_amount=Decimal("0")),
    )
    assert result.status == "partial"
    assert result.missing[0].part_number == "P-1"


def test_l1_with_children_expands_l2_qty_product() -> None:
    """有子件 L1 无一口价 → 拆 L2；有效用量 = L1.qty × L2.qty。"""
    l0 = SimBomNode(
        id=1, parent_id=None, level=0, part_number="L0", part_name="A",
        qty=Decimal("1"), node_role="supply",
    )
    l1 = SimBomNode(
        id=2, parent_id=1, level=1, part_number="L1-1", part_name="分总成",
        qty=Decimal("2"), node_role="structure",
    )
    l2a = SimBomNode(
        id=3, parent_id=2, level=2, part_number="L2-A", part_name="板",
        qty=Decimal("1"), node_role="make", sort_no=1,
    )
    l2b = SimBomNode(
        id=4, parent_id=2, level=2, part_number="L2-B", part_name="螺母",
        qty=Decimal("4"), node_role="buy", sort_no=2,
    )
    result = simulate_l0(
        l0=l0,
        children_by_parent={1: [l1], 2: [l2a, l2b]},
        stamping_prices={"L2-A": Decimal("10.0000")},
        annual_prices={"L2-B": Decimal("0.0500")},
        welding=SimWeldingFee(final_amount=Decimal("1.0000")),
    )
    assert result.status == "ok"
    assert result.stamping_amount == Decimal("20.0000")  # 10 × (2×1)
    assert result.purchased_amount == Decimal("0.4000")  # 0.05 × (2×4)
    assert result.total_amount == Decimal("21.4000")


def test_l1_bundle_prunes_children() -> None:
    """有子件 L1 命中年度价 → 一口价，不 rollup L2。"""
    l0 = SimBomNode(
        id=1, parent_id=None, level=0, part_number="L0", part_name="A",
        qty=Decimal("1"), node_role="supply",
    )
    l1 = SimBomNode(
        id=2, parent_id=1, level=1, part_number="L1-BUNDLE", part_name="分总成",
        qty=Decimal("1"), node_role="structure",
    )
    l2 = SimBomNode(
        id=3, parent_id=2, level=2, part_number="L2-IGNORED", part_name="子件",
        qty=Decimal("99"), node_role="make",
    )
    result = simulate_l0(
        l0=l0,
        children_by_parent={1: [l1], 2: [l2]},
        stamping_prices={"L2-IGNORED": Decimal("100.0000")},
        annual_prices={"L1-BUNDLE": Decimal("6.8800")},
        welding=SimWeldingFee(final_amount=Decimal("0")),
    )
    assert result.status == "ok"
    assert result.bundle_amount == Decimal("6.8800")
    assert result.stamping_amount == Decimal("0.0000")
    assert all(line.source == "bundle" for line in result.lines)


# ---------------------------------------------------------------------------
# 集成：青岛 T28 2025-01
# ---------------------------------------------------------------------------


def _load_scope_from_db(
    db: Session,
) -> tuple[list[SimBomNode], dict[str, Decimal], dict[str, Decimal], dict[str, SimWeldingFee]]:
    snap = (
        db.query(BomSnapshot)
        .filter(
            BomSnapshot.location == LOCATION,
            BomSnapshot.vehicle_model == VEHICLE_MODEL,
        )
        .one_or_none()
    )
    if snap is None:
        pytest.skip(f"无 BOM: {LOCATION}/{VEHICLE_MODEL}")

    orm_nodes = db.query(BomNode).filter(BomNode.snapshot_id == snap.id).all()
    nodes = [
        SimBomNode(
            id=n.id,
            parent_id=n.parent_id,
            level=int(n.level),
            part_number=n.part_number,
            part_name=n.part_name,
            qty=Decimal(str(n.qty if n.qty is not None else 1)),
            node_role=n.node_role,
            sort_no=n.sort_no or 0,
        )
        for n in orm_nodes
    ]

    stamping_prices = {
        r.part_number: Decimal(str(r.unit_cost))
        for r in db.query(StampingPartCost)
        .filter(
            StampingPartCost.location == LOCATION,
            StampingPartCost.vehicle_model == VEHICLE_MODEL,
            StampingPartCost.year == YEAR,
            StampingPartCost.month == MONTH,
        )
        .all()
        if r.unit_cost is not None and r.calc_status == "success"
    }

    annual_prices = {
        r.part_number: Decimal(str(r.unit_price))
        for r in db.query(BomAnnualPartPrice)
        .filter(
            BomAnnualPartPrice.location == LOCATION,
            BomAnnualPartPrice.year == YEAR,
        )
        .all()
        if r.unit_price is not None
    }

    welding_by_part: dict[str, SimWeldingFee] = {}
    for r in (
        db.query(BomL0WeldingFee)
        .filter(
            BomL0WeldingFee.location == LOCATION,
            BomL0WeldingFee.vehicle_model == VEHICLE_MODEL,
            BomL0WeldingFee.year == YEAR,
            BomL0WeldingFee.bom_version == snap.bom_version,
        )
        .all()
    ):
        final = r.final_l0_welding_fee
        if final is None:
            final = r.total_l0_welding_fee or Decimal("0")
        welding_by_part[r.part_number] = SimWeldingFee(
            final_amount=Decimal(str(final)),
            other_fee=Decimal(str(r.other_fee or 0)),
            missing_price_count=int(r.missing_price_count or 0),
        )

    return nodes, stamping_prices, annual_prices, welding_by_part


def _by_part(results: list[L0SimResult]) -> dict[str, L0SimResult]:
    return {r.part_number: r for r in results}


@pytest.mark.integration
def test_qingdao_t28_2025_01_simulate_all_l0(db_session: Session) -> None:
    """青岛 T28 2025-01：全部成品按 L0→L1→L2 模拟一遍。

    看统计一览请加 -s，或打开 tests/costing/last_qingdao_t28_sim_report.txt：
      python -X utf8 -m pytest tests/costing/test_l0_assembly_simulation.py::test_qingdao_t28_2025_01_simulate_all_l0 -s -v
    """
    nodes, stamping_prices, annual_prices, welding_by_part = _load_scope_from_db(db_session)
    results = simulate_all_l0(nodes, stamping_prices, annual_prices, welding_by_part)

    report = format_simulation_report(
        results,
        title=f"青岛 / {VEHICLE_MODEL} / {YEAR}-{MONTH:02d}  全部 L0 模拟",
        stamping_price_count=len(stamping_prices),
        annual_price_count=len(annual_prices),
        welding_count=len(welding_by_part),
    )
    _REPORT_PATH.write_text(report + "\n", encoding="utf-8")
    # pytest 默认吞掉 print；加 -s 可在终端直接看到这份一览
    print("\n" + report + "\n")
    print(f"（同上内容已写入 {_REPORT_PATH}）\n")

    l0_count = sum(1 for n in nodes if n.level == 0)
    assert l0_count == 27
    assert len(results) == 27
    assert len(welding_by_part) == 27
    assert len(stamping_prices) >= 1
    assert len(annual_prices) >= 1

    ok_results = [r for r in results if r.status == "ok"]
    partial_results = [r for r in results if r.status == "partial"]
    assert len(ok_results) + len(partial_results) == 27

    for result in results:
        assert result.welding_amount >= Decimal("0")

    missing_parts = sorted({m.part_number for r in results for m in r.missing})
    assert missing_parts == [], f"仍有缺价零件: {missing_parts}"

    total_all = quantize_money(sum((r.total_amount for r in results), Decimal("0")))
    assert total_all > Decimal("0")
    assert sum(1 for r in results if r.status == "ok") == 27


@pytest.mark.integration
def test_qingdao_t28_2025_01_golden_samples(db_session: Session) -> None:
    """锁定此前手工演练过的样例成品金额（数据补齐后仍应保持）。"""
    nodes, stamping_prices, annual_prices, welding_by_part = _load_scope_from_db(db_session)
    results = _by_part(
        simulate_all_l0(nodes, stamping_prices, annual_prices, welding_by_part)
    )

    # 流水槽加强梁：L1 叶子冲压(unit_cost=直接成本+费率) + L2 年度价 rollup + 焊接
    rain = results["501006873AA"]
    assert rain.status == "ok"
    assert rain.stamping_amount == Decimal("0.9615")
    assert rain.purchased_amount == Decimal("17.1240")
    assert rain.welding_amount == Decimal("0.7020")
    assert rain.total_amount == Decimal("18.7875")

    # 低音炮安装支架
    woofer = results["501007976AA"]
    assert woofer.status == "ok"
    assert woofer.stamping_amount == Decimal("4.8929")
    assert woofer.purchased_amount == Decimal("0.2480")
    assert woofer.welding_amount == Decimal("0.4680")
    assert woofer.total_amount == Decimal("5.6089")

    # 后盖支架：无材料子件，仅焊接费
    for pn, weld in (
        ("554002084AA", Decimal("0.3130")),
        ("554002086AA", Decimal("0.3130")),
        ("554002085AA", Decimal("0.2710")),
        ("554002087AA", Decimal("0.2710")),
    ):
        row = results[pn]
        assert row.status == "ok"
        assert row.stamping_amount == Decimal("0.0000")
        assert row.purchased_amount == Decimal("0.0000")
        assert row.welding_amount == weld
        assert row.total_amount == weld


@pytest.mark.integration
def test_qingdao_t28_2025_01_bundle_and_dash_fallback(db_session: Session) -> None:
    """一口价剪枝；*-1 叶子用「-」前零件号回退冲压价。"""
    nodes, stamping_prices, annual_prices, welding_by_part = _load_scope_from_db(db_session)
    results = _by_part(
        simulate_all_l0(nodes, stamping_prices, annual_prices, welding_by_part)
    )

    # 侧围前部：L1 502003968AA 一口价 6.88
    left_side = results["502004373AA"]
    assert left_side.status == "ok"
    assert left_side.bundle_amount == Decimal("6.8800")
    assert any(
        line.part_number == "502003968AA" and line.source == "bundle"
        for line in left_side.lines
    )

    # 551001730AA-1 → 冲压表 551001730AA（unit_cost 含费率叠价）
    rear_door = results["551001730AA"]
    assert rear_door.status == "ok"
    assert rear_door.stamping_amount == Decimal("30.6687")
    assert any(
        line.part_number == "551001730AA-1" and line.source == "stamping"
        for line in rear_door.lines
    )
