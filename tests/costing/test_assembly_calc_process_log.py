"""总成核价计算过程文本 / 卡片 JSON。"""

from __future__ import annotations

from decimal import Decimal

from app.services.costing.assembly_cost.calc.process_log import (
    ProcessLogBuilder,
    compose_card_message,
    format_missing_part_label,
    operator_write_error,
    parse_card_traces,
)


def test_process_log_roundtrip_cards() -> None:
    builder = ProcessLogBuilder()
    builder.line("2026-01  芜湖/T13J/D/09")
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
    missing = [format_missing_part_label("P-MISS", None)]
    message = compose_card_message(
        status="partial",
        missing_leaf_count=2,
        missing_parts=missing,
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
        message=message,
        missing_parts=missing,
    )

    text = builder.build_text()
    assert "2026-01" in text
    assert "5010002AA" not in text
    assert message is not None
    assert "缺价 2" in message
    assert "P-MISS（缺价）" in missing

    cards = parse_card_traces(builder.build_json())
    assert len(cards) == 2
    assert cards[0]["status"] == "ok"
    assert cards[0]["should_cost"] == "12.3400"
    assert cards[1]["missing_parts"] == ["P-MISS（缺价）"]
    assert parse_card_traces("not-json") == []
    assert parse_card_traces(None) == []


def test_operator_write_error_hides_sql() -> None:
    raw = (
        "(sqlite3.IntegrityError) UNIQUE constraint failed: "
        "costing_assembly_costs.year, costing_assembly_costs.month, "
        "costing_assembly_costs.location, costing_assembly_costs.vehicle_model, "
        "costing_assembly_costs.bom_version, costing_assembly_costs.part_number "
        "[SQL: INSERT INTO costing_assembly_costs"
    )
    message = operator_write_error(Exception(raw), part_number="551001137AA")
    assert "551001137AA" in message
    assert "INSERT INTO" not in message
    assert "UNIQUE constraint failed" not in message
    assert "未保存" in message
    assert "零件号冲突" in message


def test_operator_write_error_does_not_use_insert_column_list() -> None:
    raw = (
        "(sqlite3.IntegrityError) UNIQUE constraint failed: "
        "costing_assembly_costs.year, costing_assembly_costs.source_node_id "
        "[SQL: INSERT INTO costing_assembly_costs (year, part_number, source_node_id)]"
    )
    message = operator_write_error(Exception(raw), part_number="551001137AA")
    assert "BOM 节点" in message
    assert "零件号冲突" not in message


def test_compose_card_message_welding_only() -> None:
    message = compose_card_message(
        status="partial",
        missing_leaf_count=0,
        weld_incomplete=True,
    )
    assert message == "焊接费不完整"


def test_compose_card_message_purchased_assembly() -> None:
    from app.services.costing.assembly_cost.codes import PURCHASED_ASSEMBLY_NOTE

    assert compose_card_message(status="ok", is_purchased_assembly=True) == PURCHASED_ASSEMBLY_NOTE
    assert compose_card_message(status="ok", is_purchased_assembly=False) is None
