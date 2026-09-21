"""工程变更种树：改图整条链换号。"""

from __future__ import annotations

from types import SimpleNamespace

from app.common.engineering_change_gates import (
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
)
from app.parsers.bom.models import BomParsedNode
from app.services.bom.bom.change_tree_plant.copy import excel_row_for_added_part
from app.services.bom.bom.change_tree_plant.number_map import build_number_map
from app.services.bom.bom.change_tree_plant.sketches import copied_sketch_url
from app.services.bom.bom.change_tree_plant.types import BomChangePlantSpec


def _node(
    *,
    node_id: int,
    parent_id: int | None,
    level: int,
    part_number: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=node_id,
        parent_id=parent_id,
        level=level,
        part_number=part_number,
    )


def test_revise_l2_maps_ancestor_from_file() -> None:
    spec = BomChangePlantSpec(
        change_type=CHANGE_TYPE_REVISE,
        before_assembly_part_number="501009144AA",
        after_assembly_part_number="501009144AB",
        assembly_name="后防撞梁总成",
        part_level=PART_LEVEL_L2,
        before_part_number="501009122AA",
        after_part_number="501009122AB",
        part_name="后保下安装支架",
    )
    old_nodes = [
        _node(node_id=1, parent_id=None, level=0, part_number="501009144AA"),
        _node(node_id=2, parent_id=1, level=1, part_number="501009122AA-1"),
        _node(node_id=3, parent_id=2, level=2, part_number="501009122AA"),
        _node(node_id=4, parent_id=1, level=1, part_number="501003649AA"),
        _node(node_id=5, parent_id=2, level=2, part_number="N0111931"),
    ]
    parsed_nodes = [
        BomParsedNode(
            level=0,
            parent_index=None,
            part_number="501009144AB",
            sort_no=0,
            source_row=2,
        ),
        BomParsedNode(
            level=1,
            parent_index=0,
            part_number="501009122AB-1",
            sort_no=1,
            source_row=3,
        ),
        BomParsedNode(
            level=2,
            parent_index=1,
            part_number="501009122AB",
            sort_no=2,
            source_row=3,
        ),
    ]
    mapping = build_number_map(spec, old_nodes, parsed_nodes)
    assert mapping["501009144AA"] == "501009144AB"
    assert mapping["501009122AA"] == "501009122AB"
    assert mapping["501009122AA-1"] == "501009122AB-1"
    assert "501003649AA" not in mapping
    assert "N0111931" not in mapping


def test_revise_l2_does_not_invent_ancestor_without_file_parent_row() -> None:
    spec = BomChangePlantSpec(
        change_type=CHANGE_TYPE_REVISE,
        before_assembly_part_number="501009144AA",
        after_assembly_part_number="501009144AB",
        assembly_name="后防撞梁总成",
        part_level=PART_LEVEL_L2,
        before_part_number="501009122AA",
        after_part_number="501009122AB",
        part_name="后保下安装支架",
    )
    old_nodes = [
        _node(node_id=1, parent_id=None, level=0, part_number="501009144AA"),
        _node(node_id=2, parent_id=1, level=1, part_number="501009122AA-1"),
        _node(node_id=3, parent_id=2, level=2, part_number="501009122AA"),
    ]
    mapping = build_number_map(spec, old_nodes, [])
    assert mapping["501009144AA"] == "501009144AB"
    assert mapping["501009122AA"] == "501009122AB"
    assert "501009122AA-1" not in mapping


def test_revise_l1_does_not_map_unrelated_branch() -> None:
    spec = BomChangePlantSpec(
        change_type=CHANGE_TYPE_REVISE,
        before_assembly_part_number="501006873AA",
        after_assembly_part_number="501006873AB",
        assembly_name="流水槽加强梁总成",
        part_level=PART_LEVEL_L1,
        before_part_number="501006875AA",
        after_part_number="501006875AB",
        part_name="雨刮电机安装支架Ⅰ",
    )
    old_nodes = [
        _node(node_id=1, parent_id=None, level=0, part_number="501006873AA"),
        _node(node_id=2, parent_id=1, level=1, part_number="501006875AA"),
        _node(node_id=3, parent_id=1, level=1, part_number="501005123AA-1"),
        _node(node_id=4, parent_id=3, level=2, part_number="501005123AA"),
    ]
    mapping = build_number_map(spec, old_nodes, [])
    assert mapping["501006875AA"] == "501006875AB"
    assert "501005123AA-1" not in mapping
    assert "501005123AA" not in mapping


def test_revise_plus_not_install_maps_both_specs() -> None:
    revise = BomChangePlantSpec(
        change_type=CHANGE_TYPE_REVISE,
        before_assembly_part_number="501006873AA",
        after_assembly_part_number="501006873AB",
        assembly_name="流水槽加强梁总成",
        part_level=PART_LEVEL_L1,
        before_part_number="501006875AA",
        after_part_number="501006875AB",
        part_name="雨刮电机安装支架Ⅰ",
    )
    not_install = BomChangePlantSpec(
        change_type=CHANGE_TYPE_NOT_INSTALL,
        before_assembly_part_number="501006873AA",
        after_assembly_part_number="501006873AB",
        assembly_name="流水槽加强梁总成",
        part_level=PART_LEVEL_L1,
        before_part_number="504000341AA",
        after_part_number=None,
        part_name="左胶块",
    )
    old_nodes = [
        _node(node_id=1, parent_id=None, level=0, part_number="501006873AA"),
        _node(node_id=2, parent_id=1, level=1, part_number="501006875AA"),
        _node(node_id=3, parent_id=1, level=1, part_number="504000341AA"),
    ]
    mapping = build_number_map(revise, old_nodes, [], extra_specs=(not_install,))
    assert mapping["501006873AA"] == "501006873AB"
    assert mapping["501006875AA"] == "501006875AB"
    assert mapping["504000341AA"] is None


def test_copied_sketch_keeps_old_url_when_file_has_no_image() -> None:
    file_row = BomParsedNode(
        level=1,
        parent_index=0,
        part_number="504000341AA",
        sort_no=1,
        source_row=5,
    )
    assert (
        copied_sketch_url(
            location="青岛",
            vehicle_model="T28",
            bom_version="D/00",
            part_number="501008899AA",
            file_row=file_row,
            old_sketch_url="bom/青岛/T28/D_00/sketches/2_501008899AA.png",
        )
        == "bom/青岛/T28/D_00/sketches/2_501008899AA.png"
    )
    assert (
        copied_sketch_url(
            location="青岛",
            vehicle_model="T28",
            bom_version="D/00",
            part_number="501008899AA",
            file_row=None,
            old_sketch_url="bom/青岛/T28/D_00/sketches/2_501008899AA.png",
        )
        == "bom/青岛/T28/D_00/sketches/2_501008899AA.png"
    )


def test_copied_sketch_does_not_keep_old_url_when_part_revised() -> None:
    file_row = BomParsedNode(
        level=1,
        parent_index=0,
        part_number="551005982AB",
        sort_no=1,
        source_row=5,
    )
    assert (
        copied_sketch_url(
            location="青岛",
            vehicle_model="T2AA",
            bom_version="EC-202507",
            part_number="551005982AB",
            file_row=file_row,
            old_sketch_url="bom/青岛/T2AA/D_00/sketches/5_551005982AA.png",
            copy_old_sketch=False,
        )
        is None
    )


def test_added_part_excel_row_copies_previous_sibling() -> None:
    parsed = [
        BomParsedNode(level=0, parent_index=None, part_number="L0", sort_no=0, source_row=10),
        BomParsedNode(level=1, parent_index=0, part_number="A", sort_no=1, source_row=10),
        BomParsedNode(level=1, parent_index=0, part_number="NEW", sort_no=2, source_row=11),
        BomParsedNode(level=1, parent_index=0, part_number="B", sort_no=3, source_row=12),
    ]
    row = excel_row_for_added_part(
        add_row=parsed[2],
        parsed_nodes=parsed,
        excel_row_by_part={"A": 40, "B": 50},
    )
    assert row == 40


def test_added_part_excel_row_before_first_sibling() -> None:
    parsed = [
        BomParsedNode(level=0, parent_index=None, part_number="L0", sort_no=0, source_row=10),
        BomParsedNode(level=1, parent_index=0, part_number="NEW", sort_no=1, source_row=10),
        BomParsedNode(level=1, parent_index=0, part_number="A", sort_no=2, source_row=11),
    ]
    row = excel_row_for_added_part(
        add_row=parsed[1],
        parsed_nodes=parsed,
        excel_row_by_part={"A": 40},
    )
    assert row == 39


def test_added_part_excel_row_without_sibling_is_none() -> None:
    parsed = [
        BomParsedNode(level=0, parent_index=None, part_number="L0", sort_no=0, source_row=10),
        BomParsedNode(level=1, parent_index=0, part_number="NEW", sort_no=1, source_row=11),
    ]
    row = excel_row_for_added_part(
        add_row=parsed[1],
        parsed_nodes=parsed,
        excel_row_by_part={},
    )
    assert row is None
