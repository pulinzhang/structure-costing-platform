"""采购对象分类纯函数测试。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.bom import BomSnapshot
from app.repositories.bom.bom_repository import BomNodeRepository
from app.services.bom.procurement_object.classify import (
    KIND_L0_DEGENERATE,
    KIND_L1_STAMPING,
    KIND_L1_SUBASSEMBLY,
    SECTION_ANOMALY,
    SECTION_OBJECT,
    SECTION_OTHER_LEAF,
    SUBTYPE_SPECIAL_PROCESS,
    SUBTYPE_STAMPING_BLANK,
    classify_nodes,
)


def _node(
    node_id: int,
    *,
    level: int,
    part_number: str,
    parent_id: int | None = None,
    part_name: str | None = None,
    node_role: str = "make",
    qty: Decimal | None = Decimal("1"),
    qty_unit: str = "pcs",
    material: str | None = "DC04",
    thickness_mm: Decimal | None = Decimal("0.8"),
    thickness_text: str | None = "T=0.8",
    material_mill: str | None = "宝钢",
    weld_info: str | None = None,
    remark: str | None = None,
    excel_filename: str | None = "bom.xlsx",
    excel_sheet_name: str | None = "清单",
    excel_row: int | None = 10,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=node_id,
        parent_id=parent_id,
        level=level,
        part_number=part_number,
        part_name=part_name or part_number,
        qty=qty,
        qty_unit=qty_unit,
        node_role=node_role,
        material=material,
        thickness_mm=thickness_mm,
        thickness_text=thickness_text,
        material_mill=material_mill,
        weld_info=weld_info,
        remark=remark,
        excel_filename=excel_filename,
        excel_sheet_name=excel_sheet_name,
        excel_row=excel_row,
    )


def test_classify_degenerate_l0_special_process_and_blank() -> None:
    nodes = [
        _node(
            1,
            level=0,
            part_number="501012176AA",
            node_role="supply",
            weld_info="电泳 面积",
            material=None,
            thickness_mm=None,
            thickness_text=None,
            material_mill=None,
        ),
        _node(
            2,
            level=0,
            part_number="502008112AA",
            node_role="supply",
            part_name="顶横梁Ⅱ",
        ),
    ]
    result = classify_nodes(nodes)
    kinds = {row.part_number: row for row in result.rows}
    assert kinds["501012176AA"].object_kind == KIND_L0_DEGENERATE
    assert kinds["501012176AA"].degenerate_subtype == SUBTYPE_SPECIAL_PROCESS
    assert kinds["502008112AA"].degenerate_subtype == SUBTYPE_STAMPING_BLANK
    assert kinds["501012176AA"].l0_part_number == "501012176AA"
    assert result.counts.object_l0_degenerate_count == 2
    assert result.qa_passed is True


def test_classify_subassembly_and_stamping_and_standard_leaf() -> None:
    nodes = [
        _node(10, level=0, part_number="L0-A", node_role="supply", weld_info="焊点:4"),
        _node(
            11,
            level=1,
            part_number="L1-SUB",
            parent_id=10,
            node_role="structure",
            weld_info="焊点:2",
            thickness_mm=None,
            thickness_text=None,
        ),
        _node(
            12,
            level=2,
            part_number="L2-A",
            parent_id=11,
            node_role="make",
        ),
        _node(
            13,
            level=1,
            part_number="L1-STAMP",
            parent_id=10,
            node_role="make",
            part_name="加强板",
        ),
        _node(
            14,
            level=1,
            part_number="L1-NUT",
            parent_id=10,
            node_role="buy",
            part_name="六角螺母",
            material="SWRCH",
            thickness_mm=None,
            thickness_text="M6",
            material_mill="紧固件厂",
        ),
    ]
    result = classify_nodes(nodes)
    by_pn = {row.part_number: row for row in result.rows}
    assert by_pn["L1-SUB"].section == SECTION_OBJECT
    assert by_pn["L1-SUB"].object_kind == KIND_L1_SUBASSEMBLY
    assert by_pn["L1-SUB"].l0_part_number == "L0-A"
    assert by_pn["L1-STAMP"].object_kind == KIND_L1_STAMPING
    assert by_pn["L1-NUT"].section == SECTION_OTHER_LEAF
    assert "L0-A" not in by_pn
    assert "L2-A" not in by_pn
    assert result.counts.l2_count == 1
    assert result.counts.subassembly_child_sum == 1
    assert result.qa_passed is True


def test_classify_l0_with_outsource_remark_is_anomaly_not_object() -> None:
    nodes = [
        _node(
            20,
            level=0,
            part_number="L0-OUT",
            node_role="supply",
            remark="凸焊总成供货",
        ),
        _node(
            21,
            level=1,
            part_number="L1-A",
            parent_id=20,
            node_role="make",
        ),
    ]
    result = classify_nodes(nodes)
    by_pn = {row.part_number: row for row in result.rows}
    assert by_pn["L0-OUT"].section == SECTION_ANOMALY
    assert by_pn["L0-OUT"].object_kind is None
    assert by_pn["L0-OUT"].l0_part_number == "L0-OUT"
    assert by_pn["L1-A"].object_kind == KIND_L1_STAMPING
    object_l0 = [r for r in result.rows if r.section == SECTION_OBJECT and r.level == 0]
    assert object_l0 == []
    assert result.qa_passed is True


def test_t13j_from_main_db_if_present(db_session) -> None:
    """现网主库若有 T13J 材料清单，断言金标准结构计数。"""
    snapshot = (
        db_session.query(BomSnapshot)
        .filter(BomSnapshot.vehicle_model == "T13J")
        .order_by(BomSnapshot.id.desc())
        .first()
    )
    if snapshot is None:
        pytest.skip("主库无 T13J BOM snapshot")
    nodes = BomNodeRepository().list_by_snapshot(db_session, snapshot.id)
    if not nodes:
        pytest.skip("T13J snapshot 无节点")
    result = classify_nodes(nodes)
    assert result.counts.l0_count == 44
    assert result.counts.l0_with_children_count == 30
    assert result.counts.object_l0_degenerate_count == 14
    assert result.counts.object_l1_subassembly_count == 53
    l1_leaves = result.counts.object_l1_stamping_count + result.counts.other_leaf_count
    assert l1_leaves == 152
    assert result.counts.l2_count == 108
    assert result.counts.subassembly_child_sum == 108
    assert result.qa_passed is True
    special = {
        row.part_number for row in result.rows if row.degenerate_subtype == SUBTYPE_SPECIAL_PROCESS
    }
    assert special == {
        "501012176AA",
        "554003393AA",
        "403014115AA",
        "403014116AA",
        "T15-3301097",
        "T15-3301098",
    }
