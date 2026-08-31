"""焊接费计算：按 level 过滤、金额只含本节点、已审按行跳过。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.common.audit import AUDIT_APPROVED, SYSTEM_USER
from app.exceptions.base import BusinessException
from app.schemas.dto.bom_welding_fee_dto import BomWeldingFeeCalcDTO
from app.services.bom.welding_fee.calc.orchestrator.batch_engine import BatchCalculationEngine
from app.services.bom.welding_fee.calc.orchestrator.node_fee import CALC_OK, NodeFeeCalcParts
from app.services.bom.welding_fee.calc.orchestrator.prep import prepare_calc_run
from app.services.bom.welding_fee.calc.orchestrator.progress import ProgressNotifier


def _node(*, node_id: int, level: int, part_number: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=node_id,
        level=level,
        part_number=part_number,
        part_name=part_number,
        customer_name=None,
        weld_info_raw="点焊：1",
        lines=[],
        process_line_count=1,
    )


def _deps(nodes: list[SimpleNamespace]) -> MagicMock:
    deps = MagicMock()
    deps.unit_price_repo.list_by_location_year.return_value = [
        SimpleNamespace(item_name="点焊", unit_price=Decimal("1"), unit="点")
    ]
    deps.breakdown_repo.list_by_scope.return_value = nodes
    return deps


def test_prep_all_levels_when_levels_omitted() -> None:
    nodes = [_node(node_id=1, level=0, part_number="A"), _node(node_id=2, level=1, part_number="B")]
    ctx = prepare_calc_run(
        MagicMock(),
        _deps(nodes),
        BomWeldingFeeCalcDTO(
            year=2026,
            location="青岛",
            vehicle_model="T28",
            bom_version="D-00",
        ),
        ProgressNotifier(),
    )
    assert [n.id for n in ctx.nodes] == [1, 2]


def test_prep_levels_zero_skips_l1() -> None:
    nodes = [_node(node_id=1, level=0, part_number="A"), _node(node_id=2, level=1, part_number="B")]
    ctx = prepare_calc_run(
        MagicMock(),
        _deps(nodes),
        BomWeldingFeeCalcDTO(
            year=2026,
            location="青岛",
            vehicle_model="T28",
            bom_version="D-00",
            levels=[0],
        ),
        ProgressNotifier(),
    )
    assert [n.id for n in ctx.nodes] == [1]


def test_prep_empty_after_filter_raises() -> None:
    nodes = [_node(node_id=2, level=1, part_number="B")]
    with pytest.raises(BusinessException, match="未找到焊接工艺拆解节点"):
        prepare_calc_run(
            MagicMock(),
            _deps(nodes),
            BomWeldingFeeCalcDTO(
                year=2026,
                location="青岛",
                vehicle_model="T28",
                bom_version="D-00",
                levels=[0],
            ),
            ProgressNotifier(),
        )


def test_batch_writes_level_and_skips_approved_l0_only() -> None:
    l0 = _node(node_id=10, level=0, part_number="L0P")
    l1 = _node(node_id=11, level=1, part_number="L1P")
    ctx = SimpleNamespace(
        year=2026,
        location="青岛",
        vehicle_model="T28",
        bom_version="D-00",
        price_map={},
        nodes=[l0, l1],
        detail_lines=[],
    )
    deps = MagicMock()

    def get_by_key(**kwargs):
        if kwargs["source_breakdown_node_id"] == 10:
            return SimpleNamespace(audit_status=AUDIT_APPROVED, other_fee=None)
        return None

    deps.fee_repo.get_by_business_key.side_effect = lambda db, **kwargs: get_by_key(**kwargs)

    def fake_calc(node, price_map):
        fee = Decimal("8.0000") if node.level == 0 else Decimal("1.5000")
        return NodeFeeCalcParts(
            process_line_count=1,
            matched_line_count=1,
            missing_price_count=0,
            total_welding_fee=fee,
            calc_status=CALC_OK,
            calc_message=None,
            items=[],
        )

    with patch(
        "app.services.bom.welding_fee.calc.orchestrator.batch_engine.calc_node_fee",
        side_effect=fake_calc,
    ):
        outcome = BatchCalculationEngine(deps).run(
            MagicMock(),
            ctx=ctx,
            current_user=SYSTEM_USER,
            calc_batch_id="b1",
            progress=ProgressNotifier(),
        )

    assert outcome.skipped_approved_count == 1
    assert len(outcome.upsert_rows) == 1
    row = outcome.upsert_rows[0]
    assert row.level == 1
    assert row.part_number == "L1P"
    assert row.total_welding_fee == Decimal("1.5000")
    assert row.source_breakdown_node_id == 11


def test_staff_report_speaks_plain_language() -> None:
    from app.services.bom.welding_fee.calc.staff_report import (
        FailedNodeNote,
        format_failed_staff_section,
    )

    text = "\n".join(
        format_failed_staff_section(
            [
                FailedNodeNote(
                    level=0,
                    part_number="501012176AA",
                    part_name="中支撑",
                    weld_info_raw="电泳黑漆：0.098m2",
                    calc_message="无焊接工艺明细",
                    excel_row=128,
                    excel_filename="芜湖_T13J_材料清单.xlsx",
                    sheet_name="材料清单",
                ),
                FailedNodeNote(
                    level=1,
                    part_number="502007710AA-1",
                    part_name="左后尾灯安装板分总成",
                    weld_info_raw="凸焊:：2",
                    calc_message="无焊接工艺明细",
                    excel_row=256,
                    excel_filename="芜湖_T13J_材料清单.xlsx",
                    sheet_name="材料清单",
                ),
            ]
        )
    )
    assert "L0  501012176AA  中支撑" in text
    assert "Excel「芜湖_T13J_材料清单.xlsx」" in text
    assert "第 128 行" in text
    assert "第 256 行" in text
    assert "上传材料清单" in text
    assert "焊信原文：电泳黑漆：0.098m2" in text
    assert "L1  502007710AA-1  左后尾灯安装板分总成" in text
    assert "凸焊:：2" in text
    assert "连续冒号" in text
    assert "电泳" in text


def test_batch_failed_notes_include_weld_info() -> None:
    from app.services.bom.welding_fee.calc.orchestrator.node_fee import CALC_FAILED

    node = _node(node_id=3, level=0, part_number="501012176AA")
    node.part_name = "中支撑"
    node.weld_info_raw = "电泳黑漆：0.098m2"
    node.excel_row = 128
    ctx = SimpleNamespace(
        year=2026,
        location="芜湖",
        vehicle_model="T13J",
        bom_version="D/09",
        price_map={},
        nodes=[node],
        detail_lines=[],
        source_excel_filename="芜湖_T13J_材料清单.xlsx",
        source_sheet_name="材料清单",
    )
    deps = MagicMock()
    deps.fee_repo.get_by_business_key.return_value = None

    def fake_calc(_node, _price_map):
        return NodeFeeCalcParts(
            process_line_count=0,
            matched_line_count=0,
            missing_price_count=0,
            total_welding_fee=Decimal("0"),
            calc_status=CALC_FAILED,
            calc_message="无焊接工艺明细",
            items=[],
        )

    with patch(
        "app.services.bom.welding_fee.calc.orchestrator.batch_engine.calc_node_fee",
        side_effect=fake_calc,
    ):
        outcome = BatchCalculationEngine(deps).run(
            MagicMock(),
            ctx=ctx,
            current_user=SYSTEM_USER,
            calc_batch_id="b2",
            progress=ProgressNotifier(),
        )

    assert outcome.failed_count == 1
    assert outcome.failed_notes[0].part_number == "501012176AA"
    assert outcome.failed_notes[0].excel_row == 128
    assert outcome.failed_notes[0].excel_filename == "芜湖_T13J_材料清单.xlsx"
    assert "拆解没拆出工艺行" in (outcome.upsert_rows[0].calc_message or "")
