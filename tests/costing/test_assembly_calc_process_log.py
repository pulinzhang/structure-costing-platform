"""总成核价计算过程文本 / 卡片 JSON。"""

from __future__ import annotations

from decimal import Decimal

from app.services.costing.assembly_cost.calc.process_log import (
    ProcessLogBuilder,
    parse_card_traces,
)


def test_process_log_roundtrip_cards() -> None:
    builder = ProcessLogBuilder()
    builder.section("范围")
    builder.line("核价期: 2026-01")
    builder.add_card(
        part_number="5010001AA",
        part_name="总成",
        level=0,
        is_tree_root=True,
        object_kind=None,
        status="ok",
        should_cost=Decimal("12.3400"),
        grand_total=Decimal("13.0000"),
        material_amount=Decimal("10.0000"),
        welding_amount=Decimal("2.3400"),
        missing_leaf_count=0,
    )
    builder.add_card(
        part_number="5010002AA",
        part_name="分总成",
        level=1,
        is_tree_root=False,
        object_kind="l1_subassembly",
        status="partial",
        should_cost=Decimal("1.0000"),
        grand_total=Decimal("1.0000"),
        material_amount=Decimal("1.0000"),
        welding_amount=Decimal("0.0000"),
        missing_leaf_count=2,
        message="缺叶子价",
        missing_parts=["P-MISS（missing）"],
    )

    text = builder.build_text()
    assert "=== 范围 ===" in text
    assert "[OK] L0 5010001AA" in text
    assert "[PARTIAL] L1 5010002AA" in text

    cards = parse_card_traces(builder.build_json())
    assert len(cards) == 2
    assert cards[0]["status"] == "ok"
    assert cards[0]["should_cost"] == "12.3400"
    assert cards[1]["missing_parts"] == ["P-MISS（missing）"]
    assert parse_card_traces("not-json") == []
    assert parse_card_traces(None) == []
