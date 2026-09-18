"""工程变更种树：改图整条链换号。"""

from __future__ import annotations

from types import SimpleNamespace

from app.common.engineering_change_gates import (
    CHANGE_TYPE_REVISE,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
)
from app.parsers.bom.models import BomParsedNode
from app.services.bom.change_tree_plant import BomChangePlantSpec, _build_number_map


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


def test_revise_l2_bumps_ancestor_subassembly() -> None:
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
    mapping = _build_number_map(spec, old_nodes, parsed_nodes)
    assert mapping["501009144AA"] == "501009144AB"
    assert mapping["501009122AA"] == "501009122AB"
    assert mapping["501009122AA-1"] == "501009122AB-1"
    assert "501003649AA" not in mapping
    assert "N0111931" not in mapping


def test_revise_l2_bumps_ancestor_without_file_parent_row() -> None:
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
    mapping = _build_number_map(spec, old_nodes, [])
    assert mapping["501009122AA-1"] == "501009122AB-1"


def test_revise_l1_does_not_bump_unrelated_branch() -> None:
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
    mapping = _build_number_map(spec, old_nodes, [])
    assert mapping["501006875AA"] == "501006875AB"
    assert "501005123AA-1" not in mapping
    assert "501005123AA" not in mapping
