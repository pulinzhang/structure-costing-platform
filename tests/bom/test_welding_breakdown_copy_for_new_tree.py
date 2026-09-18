"""合册拆解：从旧树结果抄（主表+全部明细），禁止按焊信重拆。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.bom.welding_process_breakdown.generate_service import (
    BomWeldingProcessBreakdownGenerateService,
)


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=1, username="tester", display_name="测试员")


def test_copy_for_new_tree_copies_all_lines_without_reparse() -> None:
    service = BomWeldingProcessBreakdownGenerateService()
    service.snapshot_repository = MagicMock()
    service.node_repository = MagicMock()
    service.repository = MagicMock()

    snapshot = SimpleNamespace(
        id=10,
        location="青岛",
        customer_name="奇瑞",
        vehicle_model="T28",
        bom_version="D/00",
    )
    service.snapshot_repository.get_by_id.return_value = snapshot

    old_l0 = SimpleNamespace(
        id=1,
        parent_id=None,
        part_number="144AA",
        part_name="旧总成",
        level=0,
        node_role="supply",
        qty=Decimal("1"),
        qty_unit="pcs",
        excel_row=3,
        snapshot_id=10,
        weld_info="焊点：99",
    )
    new_l0 = SimpleNamespace(
        id=101,
        parent_id=None,
        part_number="144AB",
        part_name="新总成",
        level=0,
        node_role="supply",
        qty=Decimal("1"),
        qty_unit="pcs",
        excel_row=3,
        snapshot_id=10,
        weld_info="焊点：99",
    )
    service.node_repository.list_by_snapshot.return_value = [old_l0, new_l0]

    old_line_a = SimpleNamespace(
        line_no=1,
        process_token="焊点",
        matched_span="焊点：99",
        process_qty=Decimal("120"),  # 手工改过，不是原文 99
        process_qty_unit="个",
        process_qty_secondary=None,
        process_qty_secondary_unit=None,
        standard_process_name="电阻点焊",
        standard_process_unit="个",
        map_status="ready",
        rollup_flag="rolled_in_parent",
        child_fastener_qty_sum=None,
        qty_check_status="skipped",
        qty_check_detail=None,
    )
    old_line_b = SimpleNamespace(
        line_no=2,
        process_token="凸焊",
        matched_span="凸焊：7",
        process_qty=Decimal("7"),
        process_qty_unit="个",
        process_qty_secondary=None,
        process_qty_secondary_unit=None,
        standard_process_name="植/螺柱/凸焊",
        standard_process_unit="个",
        map_status="ready",
        rollup_flag="own",
        child_fastener_qty_sum=None,
        qty_check_status="skipped",
        qty_check_detail=None,
    )
    old_breakdown = SimpleNamespace(
        source_node_id=1,
        weld_info_raw="焊点：99 凸焊：7",
        parse_status="ok",
        process_line_count=2,
        qa_note=None,
        lines=[old_line_a, old_line_b],
    )
    service.repository.list_by_source_node_ids.return_value = [old_breakdown]

    created_node = SimpleNamespace(id=501, level=0, source_node_id=101, lines=[])
    service.repository.create_node.return_value = created_node
    service.repository.get_node_by_id.return_value = created_node
    service.repository.create_line.side_effect = lambda *_args, **_kwargs: SimpleNamespace()

    with patch(
        "app.parsers.bom.welding_process_breakdown_parser.parse_welding_info_text"
    ) as mock_parse:
        ids = service.copy_for_new_tree(
            MagicMock(),
            snapshot_id=10,
            source_id_remap={1: 101},
            current_user=_user(),  # type: ignore[arg-type]
        )

    assert ids == [501]
    mock_parse.assert_not_called()
    node_write = service.repository.create_node.call_args.args[1]
    assert node_write.source_node_id == 101
    assert node_write.part_number == "144AB"
    assert node_write.weld_info_raw == "焊点：99 凸焊：7"
    assert node_write.process_line_count == 2
    assert service.repository.create_line.call_count == 2
    first_line = service.repository.create_line.call_args_list[0].args[1]
    second_line = service.repository.create_line.call_args_list[1].args[1]
    assert first_line.process_qty == Decimal("120")
    assert first_line.part_number == "144AB"
    assert first_line.rollup_flag == "own"
    assert second_line.process_token == "凸焊"
    assert second_line.line_no == 2


def test_copy_for_new_tree_skips_when_remap_empty() -> None:
    service = BomWeldingProcessBreakdownGenerateService()
    service.snapshot_repository = MagicMock()
    ids = service.copy_for_new_tree(
        MagicMock(),
        snapshot_id=10,
        source_id_remap={},
        current_user=_user(),  # type: ignore[arg-type]
    )
    assert ids == []
    service.snapshot_repository.get_by_id.assert_not_called()
