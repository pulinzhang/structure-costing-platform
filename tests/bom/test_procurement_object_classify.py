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
from app.services.bom.procurement_object.generate_log_service import (
    BomProcurementObjectGenerateLogService,
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
    internal_number: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=node_id,
        parent_id=parent_id,
        level=level,
        part_number=part_number,
        part_name=part_name or part_number,
        internal_number=internal_number,
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
    assert result.counts.object_l0_special_process_count == 1
    assert result.counts.object_l0_stamping_blank_count == 1
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
            internal_number="ACA-SUB",
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
            internal_number="ACA674001",
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
    assert by_pn["L1-STAMP"].internal_number == "ACA674001"
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
            internal_number="ACA001",
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
    assert result.counts.object_l0_degenerate_count >= 14
    assert result.counts.object_l0_special_process_count >= 6
    assert result.qa_passed is True
    special = {
        row.part_number for row in result.rows if row.degenerate_subtype == SUBTYPE_SPECIAL_PROCESS
    }
    assert {
        "501012176AA",
        "554003393AA",
        "403014115AA",
        "403014116AA",
        "T15-3301097",
        "T15-3301098",
    } <= special


def test_l0_children_without_internal_number_are_degenerate() -> None:
    nodes = [
        _node(30, level=0, part_number="L0-BLANK", node_role="supply", part_name="毛坯总成"),
        _node(31, level=1, part_number="L1-NO-ERP", parent_id=30, node_role="make"),
        _node(32, level=1, part_number="L1-ALSO", parent_id=30, node_role="buy", part_name="螺母"),
    ]
    result = classify_nodes(nodes)
    by_pn = {row.part_number: row for row in result.rows}
    assert by_pn["L0-BLANK"].object_kind == KIND_L0_DEGENERATE
    assert "L1-NO-ERP" not in by_pn
    assert "L1-ALSO" not in by_pn
    assert result.counts.object_l0_degenerate_count == 1
    assert result.counts.object_l1_stamping_count == 0
    assert result.qa_passed is True


def test_l0_with_any_child_internal_number_is_not_degenerate() -> None:
    nodes = [
        _node(40, level=0, part_number="L0-MIX", node_role="supply"),
        _node(
            41,
            level=1,
            part_number="L1-ERP",
            parent_id=40,
            node_role="make",
            internal_number="ACA100",
        ),
        _node(42, level=1, part_number="L1-EMPTY", parent_id=40, node_role="make"),
    ]
    result = classify_nodes(nodes)
    by_pn = {row.part_number: row for row in result.rows}
    assert "L0-MIX" not in by_pn
    assert by_pn["L1-ERP"].object_kind == KIND_L1_STAMPING
    assert by_pn["L1-EMPTY"].section == SECTION_OTHER_LEAF
    assert by_pn["L1-EMPTY"].object_kind is None
    assert result.qa_passed is True


def test_l0_grandchild_internal_number_does_not_block_degenerate() -> None:
    nodes = [
        _node(50, level=0, part_number="L0-DEEP", node_role="supply"),
        _node(
            51,
            level=1,
            part_number="L1-SUB",
            parent_id=50,
            node_role="structure",
            weld_info="焊点:1",
            thickness_mm=None,
            thickness_text=None,
        ),
        _node(
            52,
            level=2,
            part_number="L2-ERP",
            parent_id=51,
            node_role="make",
            internal_number="ACA200",
        ),
    ]
    result = classify_nodes(nodes)
    by_pn = {row.part_number: row for row in result.rows}
    assert by_pn["L0-DEEP"].object_kind == KIND_L0_DEGENERATE
    assert "L1-SUB" not in by_pn
    assert "L2-ERP" not in by_pn
    assert result.qa_passed is True


def test_l1_without_internal_number_is_not_procurement_object() -> None:
    nodes = [
        _node(60, level=0, part_number="L0-DOOR", node_role="supply"),
        _node(
            61,
            level=1,
            part_number="551003096AA",
            parent_id=60,
            node_role="make",
            part_name="加强板",
            internal_number="ACA674001",
        ),
        _node(
            62,
            level=1,
            part_number="FQ114D0612T21F19E",
            parent_id=60,
            node_role="buy",
            part_name="弧焊焊接螺柱与盖形螺母组合件",
            material="SWRCH",
            thickness_mm=None,
            thickness_text=None,
            material_mill=None,
        ),
        _node(
            63,
            level=1,
            part_number="B11-4102613",
            parent_id=60,
            node_role="buy",
            part_name="点焊胶",
            material=None,
            thickness_mm=None,
            thickness_text=None,
            material_mill=None,
        ),
    ]
    result = classify_nodes(nodes)
    by_pn = {row.part_number: row for row in result.rows}
    assert "L0-DOOR" not in by_pn
    assert by_pn["551003096AA"].object_kind == KIND_L1_STAMPING
    assert by_pn["FQ114D0612T21F19E"].section == SECTION_OTHER_LEAF
    assert by_pn["FQ114D0612T21F19E"].object_kind is None
    assert by_pn["B11-4102613"].section == SECTION_OTHER_LEAF
    assert by_pn["B11-4102613"].object_kind is None
    assert result.qa_passed is True


def test_generate_log_lists_degenerate_subtype_counts() -> None:
    text = BomProcurementObjectGenerateLogService._success_detail(
        location="芜湖",
        vehicle_model="T13J",
        bom_version="D/09",
        node_count=357,
        object_count=14 + 53 + 80,
        other_leaf_count=72,
        anomaly_count=0,
        qa_passed=True,
        object_l0_degenerate_count=14,
        object_l0_special_process_count=6,
        object_l0_stamping_blank_count=8,
        object_l1_subassembly_count=53,
        object_l1_stamping_count=80,
    )
    assert "退化供货件亚类：特殊工艺 6 / 冲压毛坯 8" in text
    assert "冲压毛坯 8 件（可发货；无焊信则不编处理费）" in text
    assert "已按毛坯供货" not in text
