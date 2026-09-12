"""计算报告序号与采购协议同一口径。"""

from __future__ import annotations

from types import SimpleNamespace

from app.services.costing.assembly_cost.calc.seq_label import calc_card_seq_labels


def _node(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def _po(**kwargs: object) -> SimpleNamespace:
    payload = {
        "section": "object",
        "excel_row": 0,
        "part_name": None,
        "internal_number": None,
        "supplier_name": None,
        "l0_part_number": "L0",
        "object_kind": None,
    }
    payload.update(kwargs)
    return SimpleNamespace(**payload)


def test_calc_seq_labels_match_procurement_agreement() -> None:
    root = _node(id=10, parent_id=None, seq_no=5, sort_no=1, part_number="L0")
    stamping = _node(id=11, parent_id=10, seq_no=None, sort_no=2, part_number="S1")
    sub = _node(id=12, parent_id=10, seq_no=None, sort_no=3, part_number="A1")
    labels = calc_card_seq_labels(
        [root, stamping, sub],
        [
            _po(
                source_node_id=11,
                part_number="S1",
                object_kind="l1_stamping",
                l0_part_number="L0",
            ),
            _po(
                source_node_id=12,
                part_number="A1",
                object_kind="l1_subassembly",
                l0_part_number="L0",
            ),
        ],
        {10, 11, 12},
    )
    assert labels[10] == "5"
    assert labels[11] == "5-1"
    assert labels[12] == "5-2"


def test_degenerate_supply_seq_is_plain_number() -> None:
    root = _node(id=20, parent_id=None, seq_no=5, sort_no=1, part_number="L0")
    labels = calc_card_seq_labels(
        [root],
        [
            _po(
                source_node_id=20,
                part_number="L0",
                object_kind="l0_degenerate",
                l0_part_number="L0",
            ),
        ],
        {20},
    )
    assert labels[20] == "5"
    assert "-" not in labels[20]
