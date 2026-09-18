"""工程变更工艺硬门禁与序号校验。"""

from __future__ import annotations

import pytest

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_REVISE,
    EC_SEQ_MISMATCH,
    PART_LEVEL_ASSEMBLY,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
)
from app.exceptions.base import BusinessException
from app.parsers.bom.models import BomParsedNode
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed
from app.services.engineering_change.upload.gates.process_gates import (
    discover_bom_process_news,
    validate_bom_seq_matches,
)


def _change_order(
    *,
    change_type: str = CHANGE_TYPE_REVISE,
    part_level: str = PART_LEVEL_ASSEMBLY,
    before_part: str | None = None,
    after_part: str | None = None,
) -> ChangeOrderRowParsed:
    return ChangeOrderRowParsed(
        project_code="T13J",
        effective_period_text="2026年08月",
        change_type=change_type,
        before_assembly_part_number="551003086AA",
        after_assembly_part_number="551003086AB",
        assembly_name="铰链",
        part_level=part_level,
        before_part_number=before_part,
        after_part_number=after_part,
        part_name=None,
        excel_row=2,
    )


def test_validate_bom_seq_mismatch() -> None:
    nodes = [
        BomParsedNode(
            level=0,
            parent_index=None,
            part_number="551003086AB",
            part_name="x",
            seq_no=9,
            sort_no=0,
            source_row=2,
        )
    ]
    with pytest.raises(BusinessException) as exc:
        validate_bom_seq_matches(nodes, before_seq_no=5)
    assert str(exc.value) == EC_SEQ_MISMATCH


def test_validate_bom_seq_empty_ok() -> None:
    nodes = [
        BomParsedNode(
            level=0,
            parent_index=None,
            part_number="551003086AB",
            part_name="x",
            seq_no=None,
            sort_no=0,
            source_row=2,
        )
    ]
    validate_bom_seq_matches(nodes, before_seq_no=5)


def test_discover_change_order_part_bump() -> None:
    change_order = _change_order(
        part_level=PART_LEVEL_L1,
        before_part="501006875AA",
        after_part="501006875AB",
    )
    bumps, adds = discover_bom_process_news(
        change_order=change_order,
        old_tree_numbers={"551003086AA", "501006875AA"},
        parsed_nodes=[],
    )
    assert bumps == {"501006875AA": "501006875AB"}
    assert adds == set()


def test_discover_file_letter_bump_and_add() -> None:
    change_order = _change_order()
    bumps, adds = discover_bom_process_news(
        change_order=change_order,
        old_tree_numbers={"501006875AA", "501009122AA"},
        parsed_nodes=[
            BomParsedNode(
                level=1,
                parent_index=0,
                part_number="501006875AB",
                part_name="a",
                sort_no=1,
                source_row=3,
            ),
            BomParsedNode(
                level=1,
                parent_index=0,
                part_number="501007040AA",
                part_name="new",
                sort_no=2,
                source_row=4,
            ),
        ],
    )
    assert bumps["501006875AA"] == "501006875AB"
    assert "501007040AA" in adds


def test_discover_add_part_change_order() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_ADD_PART,
        part_level=PART_LEVEL_L1,
        before_part=None,
        after_part="501007040AA",
    )
    bumps, adds = discover_bom_process_news(
        change_order=change_order,
        old_tree_numbers={"551003086AA"},
        parsed_nodes=[],
    )
    assert bumps == {}
    assert adds == {"501007040AA"}


def test_letter_version_helpers_roundtrip() -> None:
    from app.common.engineering_change_gates import (
        bump_letter_version,
        find_letter_predecessor_number,
        is_letter_version_bump,
        letter_version_base,
        letter_version_suffix,
    )

    assert letter_version_base("501006875AB") == "501006875"
    assert is_letter_version_bump("501006875AA", "501006875AB")
    assert not is_letter_version_bump("501006875AB", "501006875AA")
    assert (
        find_letter_predecessor_number(["501006875AA", "501006875AB", "501009122AA"], "501006875AC")
        == "501006875AB"
    )
    assert letter_version_suffix("501009122AA-1") == "AA"
    assert letter_version_base("501009122AA-1") == "501009122-1"
    assert letter_version_base("501009122AB-1") == "501009122-1"
    assert is_letter_version_bump("501009122AA-1", "501009122AB-1")
    assert not is_letter_version_bump("501009122AA", "501009122AB-1")
    assert bump_letter_version("501009122AA-1") == "501009122AB-1"
    assert (
        find_letter_predecessor_number(["501009122AA-1", "501009122AA"], "501009122AB-1")
        == "501009122AA-1"
    )


def test_discover_file_letter_bump_subassembly() -> None:
    change_order = _change_order(
        part_level=PART_LEVEL_L2,
        before_part="501009122AA",
        after_part="501009122AB",
    )
    bumps, adds = discover_bom_process_news(
        change_order=change_order,
        old_tree_numbers={"501009144AA", "501009122AA-1", "501009122AA", "N0111931"},
        parsed_nodes=[
            BomParsedNode(
                level=1,
                parent_index=0,
                part_number="501009122AB-1",
                part_name="后保下安装支架总成",
                sort_no=1,
                source_row=3,
            ),
            BomParsedNode(
                level=2,
                parent_index=1,
                part_number="501009122AB",
                part_name="后保下安装支架",
                sort_no=2,
                source_row=3,
            ),
        ],
    )
    assert bumps["501009122AA"] == "501009122AB"
    assert bumps["501009122AA-1"] == "501009122AB-1"
    assert adds == set()


def test_add_stamping_needs_process_standard_and_glue_do_not() -> None:
    from decimal import Decimal

    from app.services.engineering_change.upload.gates.process_gates import (
        _parsed_needs_process,
    )

    l0 = BomParsedNode(
        level=0,
        parent_index=None,
        part_number="501006873AB",
        part_name="总成",
        sort_no=0,
        source_row=2,
    )
    stamping = BomParsedNode(
        level=1,
        parent_index=0,
        part_number="501007040AA",
        part_name="中通道后纵梁加强板",
        material="HC340/590DP",
        thickness_mm=Decimal("1.0"),
        sort_no=1,
        source_row=3,
        node_role="make",
    )
    glue = BomParsedNode(
        level=1,
        parent_index=0,
        part_number="504000341AA",
        part_name="左D柱下结构增强胶块",
        material="PA6+GF36",
        thickness_text="发泡料（环氧树脂等）",
        qty_unit="pcs",
        sort_no=2,
        source_row=4,
        node_role="make",
    )
    nut = BomParsedNode(
        level=1,
        parent_index=0,
        part_number="N0111931",
        part_name="焊接螺母",
        sort_no=3,
        source_row=5,
        node_role="buy",
    )
    sub_assembly = BomParsedNode(
        level=1,
        parent_index=0,
        part_number="501009122AB-1",
        part_name="后保下安装支架分总成",
        sort_no=4,
        source_row=6,
        node_role="structure",
    )
    child = BomParsedNode(
        level=2,
        parent_index=4,
        part_number="501009122AB",
        part_name="后保下安装支架",
        sort_no=5,
        source_row=6,
        node_role="make",
        thickness_mm=Decimal("1.5"),
    )
    nodes = [l0, stamping, glue, nut, sub_assembly, child]
    assert _parsed_needs_process(nodes, stamping) is True
    assert _parsed_needs_process(nodes, glue) is False
    assert _parsed_needs_process(nodes, nut) is False
    assert _parsed_needs_process(nodes, sub_assembly) is False
