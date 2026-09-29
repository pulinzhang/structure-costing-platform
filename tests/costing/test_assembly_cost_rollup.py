"""总成 rollup：外购件总成卡根命中年度价后不再拆子件报缺价。"""

from __future__ import annotations

from decimal import Decimal

from app.common.system_defaults import (
    DEFAULT_FINISHED_FINANCE_RATE,
    DEFAULT_FINISHED_MANAGEMENT_RATE,
    DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
    DEFAULT_FINISHED_SCRAP_RATE,
)
from app.services.costing.assembly_cost.calc.rollup import rollup_assembly
from app.services.costing.assembly_cost.calc.rollup_models import (
    RollupBomNode,
    RollupFinishedRates,
    RollupWeldingFee,
)


def _node(
    node_id: int,
    *,
    parent_id: int | None,
    level: int,
    part_number: str,
    part_name: str | None = None,
    qty: str = "1",
    node_role: str = "structure",
    sort_no: int = 0,
    seq_no: int | None = None,
    excel_row: int | None = None,
) -> RollupBomNode:
    return RollupBomNode(
        id=node_id,
        parent_id=parent_id,
        level=level,
        part_number=part_number,
        part_name=part_name,
        qty=Decimal(qty),
        node_role=node_role,
        sort_no=sort_no,
        seq_no=seq_no,
        excel_row=excel_row,
    )


def _default_rates() -> RollupFinishedRates:
    return RollupFinishedRates(
        finance_rate=DEFAULT_FINISHED_FINANCE_RATE,
        management_rate=DEFAULT_FINISHED_MANAGEMENT_RATE,
        scrap_rate=DEFAULT_FINISHED_SCRAP_RATE,
        pretax_profit_rate=DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
    )


def _children(
    nodes: list[RollupBomNode],
) -> tuple[dict[int | None, list[RollupBomNode]], dict[int, RollupBomNode]]:
    children: dict[int | None, list[RollupBomNode]] = {}
    by_id = {node.id: node for node in nodes}
    for node in nodes:
        children.setdefault(node.parent_id, []).append(node)
    return children, by_id


def test_purchased_assembly_root_uses_annual_and_skips_children() -> None:
    root = _node(
        10,
        parent_id=1,
        level=1,
        part_number="502003968AA",
        part_name="左前安全带滑轨上固定板总成",
    )
    plate = _node(
        11,
        parent_id=10,
        level=2,
        part_number="502003966AA",
        part_name="左前安全带滑轨固定板",
        sort_no=1,
    )
    nut = _node(
        12,
        parent_id=10,
        level=2,
        part_number="QR37108",
        part_name="焊接方螺母",
        node_role="buy",
        sort_no=2,
    )
    children, by_id = _children([root, plate, nut])
    result = rollup_assembly(
        root=root,
        children_by_parent=children,
        stamping_prices={},
        annual_prices={"502003968AA": Decimal("6.8800")},
        welding=RollupWeldingFee(
            final_amount=Decimal("0.1170"),
            missing_price_count=1,
            welding_fee_id=99,
            calc_status="partial",
        ),
        nodes_by_id=by_id,
        rates=_default_rates(),
    )
    by_part = {line.part_number: line for line in result.lines}
    assert result.status == "ok"
    assert result.missing_leaf_count == 0
    assert result.bundle_amount == Decimal("6.8800")
    assert result.material_amount == Decimal("6.8800")
    assert result.welding_amount == Decimal("0.0000")
    assert result.welding_fee_id is None
    assert result.should_cost == Decimal("6.8800")
    assert result.vendor_quote == Decimal("6.8800")
    assert result.gap_amount == Decimal("0.0000")
    assert by_part["502003968AA"].cost_source == "bundle"
    assert by_part["502003966AA"].cost_source == "skipped_by_bundle"
    assert by_part["QR37108"].cost_source == "skipped_by_bundle"
    assert "missing" not in {line.cost_source for line in result.lines}


def test_assembly_root_without_annual_still_reports_missing_child() -> None:
    root = _node(20, parent_id=1, level=1, part_number="502003968AA")
    plate = _node(21, parent_id=20, level=2, part_number="502003966AA", sort_no=1)
    children, by_id = _children([root, plate])
    result = rollup_assembly(
        root=root,
        children_by_parent=children,
        stamping_prices={},
        annual_prices={},
        welding=None,
        nodes_by_id=by_id,
        rates=_default_rates(),
    )
    assert result.status == "partial"
    assert result.missing_leaf_count == 1
    assert result.lines[0].part_number == "502003966AA"
    assert result.lines[0].cost_source == "missing"


def test_in_house_assembly_still_copies_own_welding() -> None:
    root = _node(25, parent_id=1, level=1, part_number="501000010AA")
    leaf = _node(
        26,
        parent_id=25,
        level=2,
        part_number="501000011AA",
        node_role="make",
        sort_no=1,
    )
    children, by_id = _children([root, leaf])
    result = rollup_assembly(
        root=root,
        children_by_parent=children,
        stamping_prices={"501000011AA": Decimal("1.0000")},
        annual_prices={},
        welding=RollupWeldingFee(final_amount=Decimal("0.1170"), welding_fee_id=7),
        nodes_by_id=by_id,
        rates=_default_rates(),
    )
    assert result.status == "ok"
    assert result.stamping_amount == Decimal("1.0000")
    assert result.welding_amount == Decimal("0.1170")
    assert result.welding_fee_id == 7
    assert result.should_cost == Decimal("1.1170")


def test_parent_still_prunes_child_bundle() -> None:
    root = _node(30, parent_id=None, level=0, part_number="501000001AA")
    purchased = _node(
        31,
        parent_id=30,
        level=1,
        part_number="502003968AA",
        qty="1",
        sort_no=1,
    )
    plate = _node(32, parent_id=31, level=2, part_number="502003966AA", sort_no=1)
    children, by_id = _children([root, purchased, plate])
    result = rollup_assembly(
        root=root,
        children_by_parent=children,
        stamping_prices={},
        annual_prices={"502003968AA": Decimal("6.8800")},
        welding=None,
        nodes_by_id=by_id,
        rates=_default_rates(),
    )
    by_part = {line.part_number: line for line in result.lines}
    assert result.status == "ok"
    assert result.bundle_amount == Decimal("6.8800")
    assert by_part["502003968AA"].cost_source == "bundle"
    assert by_part["502003966AA"].cost_source == "skipped_by_bundle"


def test_leaf_root_with_annual_is_purchased_not_bundle() -> None:
    root = _node(
        40,
        parent_id=1,
        level=1,
        part_number="QR37108",
        part_name="焊接方螺母",
        node_role="buy",
    )
    children, by_id = _children([root])
    result = rollup_assembly(
        root=root,
        children_by_parent=children,
        stamping_prices={},
        annual_prices={"QR37108": Decimal("0.2100")},
        welding=None,
        nodes_by_id=by_id,
        rates=_default_rates(),
    )
    assert result.status == "ok"
    assert result.purchased_amount == Decimal("0.2100")
    assert result.bundle_amount == Decimal("0.0000")
    assert result.lines[0].cost_source == "annual"


def test_sorted_children_same_seq_level_before_excel_row() -> None:
    from app.services.costing.assembly_cost.calc.tree import sorted_children

    deeper = _node(11, parent_id=10, level=2, part_number="L2", seq_no=5, excel_row=10, sort_no=1)
    shallower = _node(
        12, parent_id=10, level=1, part_number="L1", seq_no=5, excel_row=99, sort_no=9
    )
    children, _by_id = _children([deeper, shallower])
    ordered = sorted_children(children, 10)
    assert [node.part_number for node in ordered] == ["L1", "L2"]


def test_sorted_children_seq_no_then_level_then_excel_row() -> None:
    from app.services.costing.assembly_cost.calc.tree import sorted_children

    later_seq = _node(11, parent_id=10, level=0, part_number="A", seq_no=2, excel_row=10, sort_no=1)
    earlier_seq = _node(
        12, parent_id=10, level=0, part_number="B", seq_no=1, excel_row=99, sort_no=9
    )
    children, _by_id = _children([later_seq, earlier_seq])
    ordered = sorted_children(children, 10)
    assert [node.part_number for node in ordered] == ["B", "A"]


def test_sorted_children_same_seq_follow_copied_excel_row() -> None:
    from app.services.costing.assembly_cost.calc.tree import sorted_children

    old_left = _node(11, parent_id=10, level=1, part_number="A", seq_no=5, sort_no=1, excel_row=40)
    added = _node(99, parent_id=10, level=1, part_number="NEW", seq_no=5, sort_no=8, excel_row=40)
    old_right = _node(12, parent_id=10, level=1, part_number="B", seq_no=5, sort_no=2, excel_row=50)
    children, _by_id = _children([old_left, added, old_right])
    ordered = sorted_children(children, 10)
    assert [node.part_number for node in ordered] == ["A", "NEW", "B"]


def test_sorted_children_same_slot_aa_before_ab() -> None:
    from app.services.costing.assembly_cost.calc.tree import sorted_children

    rev_ab = _node(
        1365,
        parent_id=None,
        level=0,
        part_number="551007577AB",
        seq_no=2,
        excel_row=5,
        sort_no=4,
    )
    rev_aa = _node(
        649,
        parent_id=None,
        level=0,
        part_number="551007577AA",
        seq_no=2,
        excel_row=7,
        sort_no=4,
    )
    children, _by_id = _children([rev_ab, rev_aa])
    ordered = sorted_children(children, None)
    assert [node.part_number for node in ordered] == ["551007577AA", "551007577AB"]
