"""工程变更材料清单与旧树对齐、内部号/总成图门禁。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    EC_ADD_ALREADY_ON_TREE,
    EC_ASSEMBLY_SKETCH_REQUIRED,
    EC_INTERNAL_REQUIRED,
    EC_NOT_INSTALL_CHILDREN,
    EC_NOT_INSTALL_SIGNAL,
    EC_PART_NOT_ON_TREE,
    EC_PART_SKETCH_REQUIRED,
    EC_QTY_CHANGED,
    EC_REVISE_FILE_CHAIN,
    NOT_INSTALL_REMARK,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
)
from app.exceptions.base import BusinessException
from app.parsers.bom.models import BomParsedNode
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed
from app.services.engineering_change.upload.gates.tree_gates import (
    apply_process_sketches_to_bom_nodes,
    validate_change_tree_gates,
    validate_identity_gates,
)

_PNG = b"png"


def _old(
    *,
    node_id: int,
    parent_id: int | None,
    level: int,
    part_number: str,
    internal_number: str | None = "ACA610",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=node_id,
        parent_id=parent_id,
        level=level,
        part_number=part_number,
        internal_number=internal_number,
    )


def _file(
    *,
    level: int,
    parent_index: int | None,
    part_number: str,
    internal_number: str | None = None,
    qty: Decimal | None = Decimal("1"),
    remark: str | None = None,
    sketch_bytes: bytes | None = None,
    source_row: int = 5,
) -> BomParsedNode:
    return BomParsedNode(
        level=level,
        parent_index=parent_index,
        part_number=part_number,
        part_name="x",
        internal_number=internal_number,
        qty=qty,
        remark=remark,
        sketch_bytes=sketch_bytes,
        sort_no=level,
        source_row=source_row,
    )


def _change_order(
    *,
    change_type: str,
    part_level: str = PART_LEVEL_L1,
    before_part: str | None = None,
    after_part: str | None = None,
) -> ChangeOrderRowParsed:
    return ChangeOrderRowParsed(
        project_code="T28",
        effective_period_text="2025年07月",
        change_type=change_type,
        before_assembly_part_number="501006873AA",
        after_assembly_part_number="501006873AB",
        assembly_name="铰链",
        part_level=part_level,
        before_part_number=before_part,
        after_part_number=after_part,
        part_name=None,
        excel_row=2,
    )


def test_stop_skips_tree_gates() -> None:
    change_order = _change_order(change_type=CHANGE_TYPE_STOP, part_level="总成")
    validate_change_tree_gates(change_order, [], [])


def test_revise_before_part_must_be_on_old_tree() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_REVISE,
        before_part="501006875AA",
        after_part="501006875AB",
    )
    old_nodes = [_old(node_id=1, parent_id=None, level=0, part_number="501006873AA")]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501006873AB",
            internal_number="ACA610",
            sketch_bytes=_PNG,
        )
    ]
    with pytest.raises(BusinessException) as exc:
        validate_change_tree_gates(change_order, old_nodes, sliced)
    assert str(exc.value).startswith(EC_PART_NOT_ON_TREE)


def test_revise_l2_missing_intermediate_rejects() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_REVISE,
        part_level=PART_LEVEL_L2,
        before_part="501009122AA",
        after_part="501009122AB",
    )
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501009144AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="501009122AA-1",
            internal_number="ACA611N01",
        ),
        _old(node_id=3, parent_id=2, level=2, part_number="501009122AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501009144AB",
            internal_number="ACA611",
            sketch_bytes=_PNG,
        ),
        _file(level=2, parent_index=0, part_number="501009122AB"),
    ]
    with pytest.raises(BusinessException) as exc:
        validate_change_tree_gates(change_order, old_nodes, sliced)
    assert str(exc.value).startswith(EC_REVISE_FILE_CHAIN)


def test_revise_l2_chain_in_file_ok() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_REVISE,
        part_level=PART_LEVEL_L2,
        before_part="501009122AA",
        after_part="501009122AB",
    )
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501009144AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="501009122AA-1",
            internal_number="ACA611N01",
        ),
        _old(node_id=3, parent_id=2, level=2, part_number="501009122AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501009144AB",
            internal_number="ACA611",
            sketch_bytes=_PNG,
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="501009122AB-1",
            internal_number="ACA611N01",
        ),
        _file(level=2, parent_index=1, part_number="501009122AB"),
    ]
    validate_change_tree_gates(change_order, old_nodes, sliced)


def test_not_install_change_order_without_file_row_rejects() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_NOT_INSTALL,
        before_part="504000341AA",
    )
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501006873AA"),
        _old(node_id=2, parent_id=1, level=1, part_number="504000341AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501006873AB",
            internal_number="ACA610",
            sketch_bytes=_PNG,
        )
    ]
    with pytest.raises(BusinessException) as exc:
        validate_change_tree_gates(change_order, old_nodes, sliced)
    assert str(exc.value).startswith(EC_NOT_INSTALL_SIGNAL)


def test_not_install_children_must_be_marked() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_NOT_INSTALL,
        before_part="501009122AA-1",
    )
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501009144AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="501009122AA-1",
            internal_number="ACA611N01",
        ),
        _old(node_id=3, parent_id=2, level=2, part_number="501009122AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501009144AB",
            internal_number="ACA611",
            sketch_bytes=_PNG,
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="501009122AA-1",
            qty=Decimal("0"),
            remark=NOT_INSTALL_REMARK,
        ),
    ]
    with pytest.raises(BusinessException) as exc:
        validate_change_tree_gates(change_order, old_nodes, sliced)
    assert str(exc.value).startswith(EC_NOT_INSTALL_CHILDREN)


def test_add_already_on_tree_rejects() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_ADD_PART,
        after_part="501006875AA",
    )
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501006873AA"),
        _old(node_id=2, parent_id=1, level=1, part_number="501006875AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501006873AB",
            internal_number="ACA610",
            sketch_bytes=_PNG,
        ),
        _file(level=1, parent_index=0, part_number="501006875AA"),
    ]
    with pytest.raises(BusinessException) as exc:
        validate_change_tree_gates(change_order, old_nodes, sliced)
    assert str(exc.value).startswith(EC_ADD_ALREADY_ON_TREE)


def test_add_new_letter_version_is_not_inferred_as_revise() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_ADD_PART,
        after_part="501006875AB",
    )
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501006873AA"),
        _old(node_id=2, parent_id=1, level=1, part_number="501006875AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501006873AB",
            internal_number="ACA610",
            sketch_bytes=_PNG,
        ),
        _file(level=1, parent_index=0, part_number="501006875AB"),
    ]
    validate_change_tree_gates(change_order, old_nodes, sliced)


def test_add_qty_zero_rejects() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_ADD_PART,
        after_part="501007040AA",
    )
    old_nodes = [_old(node_id=1, parent_id=None, level=0, part_number="501006873AA")]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501006873AB",
            internal_number="ACA610",
            sketch_bytes=_PNG,
        ),
        _file(level=1, parent_index=0, part_number="501007040AA", qty=Decimal("0")),
    ]
    with pytest.raises(BusinessException) as exc:
        validate_change_tree_gates(change_order, old_nodes, sliced)
    assert str(exc.value).startswith(EC_QTY_CHANGED)


def test_add_not_install_remark_rejects() -> None:
    change_order = _change_order(
        change_type=CHANGE_TYPE_ADD_PART,
        after_part="501007040AA",
    )
    old_nodes = [_old(node_id=1, parent_id=None, level=0, part_number="501006873AA")]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501006873AB",
            internal_number="ACA610",
            sketch_bytes=_PNG,
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="501007040AA",
            remark=NOT_INSTALL_REMARK,
        ),
    ]
    with pytest.raises(BusinessException) as exc:
        validate_change_tree_gates(change_order, old_nodes, sliced)
    assert str(exc.value).startswith(EC_NOT_INSTALL_SIGNAL)


def test_identity_requires_l0_internal_and_sketch() -> None:
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501006873AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501006873AB",
            internal_number=None,
            sketch_bytes=_PNG,
        )
    ]
    with pytest.raises(BusinessException) as exc:
        validate_identity_gates(old_nodes, sliced)
    assert str(exc.value).startswith(EC_INTERNAL_REQUIRED)

    sliced[0].internal_number = "ACA610"
    sliced[0].sketch_bytes = None
    with pytest.raises(BusinessException) as exc:
        validate_identity_gates(old_nodes, sliced)
    assert str(exc.value).startswith(EC_ASSEMBLY_SKETCH_REQUIRED)


def test_identity_requires_subassembly_internal() -> None:
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501009144AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="501009122AA-1",
            internal_number="ACA611N01",
        ),
        _old(node_id=3, parent_id=2, level=2, part_number="501009122AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501009144AB",
            internal_number="ACA611",
            sketch_bytes=_PNG,
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="501009122AB-1",
            internal_number=None,
        ),
        _file(level=2, parent_index=1, part_number="501009122AB"),
    ]
    with pytest.raises(BusinessException) as exc:
        validate_identity_gates(old_nodes, sliced)
    assert str(exc.value).startswith(EC_INTERNAL_REQUIRED)


def test_identity_requires_l1_part_sketch() -> None:
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="551007577AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="551005982AA",
            internal_number="ACA610001",
        ),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="551007577AB",
            internal_number="ACA610",
            sketch_bytes=_PNG,
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="551005982AB",
            internal_number="ACA610001",
        ),
    ]
    with pytest.raises(BusinessException) as exc:
        validate_identity_gates(old_nodes, sliced)
    message = str(exc.value)
    assert message.startswith(EC_PART_SKETCH_REQUIRED)
    assert "551005982AB" in message
    assert "单件图示" in message

    sliced[1].sketch_bytes = _PNG
    validate_identity_gates(old_nodes, sliced)


def test_identity_skips_l1_part_sketch_when_not_install() -> None:
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501008897AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="504000341AA",
            internal_number="ACA611009",
        ),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501008897AB",
            internal_number="ACA611",
            sketch_bytes=_PNG,
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="504000341AA",
            internal_number="ACA611009",
            qty=Decimal("0"),
            remark=NOT_INSTALL_REMARK,
        ),
    ]
    validate_identity_gates(old_nodes, sliced)


def test_identity_skips_l1_part_sketch_when_subassembly() -> None:
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501009144AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="501009122AA-1",
            internal_number="ACA611N01",
        ),
        _old(node_id=3, parent_id=2, level=2, part_number="501009122AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501009144AB",
            internal_number="ACA611",
            sketch_bytes=_PNG,
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="501009122AB-1",
            internal_number="ACA611N01",
        ),
        _file(level=2, parent_index=1, part_number="501009122AB", sketch_bytes=_PNG),
    ]
    validate_identity_gates(old_nodes, sliced)


def test_identity_requires_l2_part_sketch() -> None:
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="501009144AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="501009122AA-1",
            internal_number="ACA611N01",
        ),
        _old(node_id=3, parent_id=2, level=2, part_number="501009122AA"),
    ]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="501009144AB",
            internal_number="ACA611",
            sketch_bytes=_PNG,
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="501009122AB-1",
            internal_number="ACA611N01",
        ),
        _file(level=2, parent_index=1, part_number="501009122AB"),
    ]
    with pytest.raises(BusinessException) as exc:
        validate_identity_gates(old_nodes, sliced)
    message = str(exc.value)
    assert message.startswith(EC_PART_SKETCH_REQUIRED)
    assert "501009122AB" in message


def test_identity_l0_merged_needs_one_assembly_sketch() -> None:
    old_nodes = [_old(node_id=1, parent_id=None, level=0, part_number="551007577AA")]
    sliced = [
        _file(
            level=0,
            parent_index=None,
            part_number="551007577AB",
            internal_number="ACA610",
            sketch_bytes=_PNG,
        ),
        _file(
            level=0,
            parent_index=None,
            part_number="551007577AB",
            internal_number="ACA610",
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="551005982AB",
            internal_number="ACA610001",
            sketch_bytes=_PNG,
        ),
    ]
    validate_identity_gates(old_nodes, sliced)


def test_apply_process_sketches_fills_missing_part_sketch() -> None:
    nodes = [
        _file(
            level=0,
            parent_index=None,
            part_number="551007577AB",
            internal_number="ACA610",
            sketch_bytes=_PNG,
        ),
        _file(
            level=1,
            parent_index=0,
            part_number="551005982AB",
            internal_number="ACA610001",
        ),
    ]
    apply_process_sketches_to_bom_nodes(nodes, {"551005982AB": _PNG})
    assert nodes[1].sketch_bytes == _PNG
    old_nodes = [_old(node_id=1, parent_id=None, level=0, part_number="551007577AA")]
    validate_identity_gates(old_nodes, nodes)


def test_t2aa_sample_blocks_missing_l1_part_sketch() -> None:
    from pathlib import Path

    from app.parsers.bom.bom_parser import parse_bom_excel
    from app.parsers.engineering_change.sheet_extract import SHEET_BOM

    sample = Path("docs/engineering-change/samples/工程变更导入T2AA-1.xlsx")
    parsed = parse_bom_excel(sample.read_bytes(), sheet_name=SHEET_BOM)
    target = next(node for node in parsed.nodes if node.part_number == "551005982AB")
    assert int(target.level) == 1
    assert not target.sketch_bytes
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="551007577AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="551005982AA",
            internal_number="ACA610001",
        ),
    ]
    with pytest.raises(BusinessException) as exc:
        validate_identity_gates(old_nodes, parsed.nodes)
    message = str(exc.value)
    assert message.startswith(EC_PART_SKETCH_REQUIRED)
    assert "551005982AB" in message
    assert "单件图示" in message


def test_t2aa_sample_copies_process_sketch_onto_bom_l1() -> None:
    from pathlib import Path

    from app.parsers.bom.bom_parser import parse_bom_excel
    from app.parsers.engineering_change.sheet_extract import SHEET_BOM
    from app.services.engineering_change.upload.gates.process_gates import (
        parse_process_part_sketches,
    )

    sample = Path("docs/engineering-change/samples/工程变更导入T2AA-1.xlsx")
    content = sample.read_bytes()
    parsed = parse_bom_excel(content, sheet_name=SHEET_BOM)
    target = next(node for node in parsed.nodes if node.part_number == "551005982AB")
    assert not target.sketch_bytes
    apply_process_sketches_to_bom_nodes(parsed.nodes, parse_process_part_sketches(content))
    assert target.sketch_bytes
    old_nodes = [
        _old(node_id=1, parent_id=None, level=0, part_number="551007577AA"),
        _old(
            node_id=2,
            parent_id=1,
            level=1,
            part_number="551005982AA",
            internal_number="ACA610001",
        ),
    ]
    validate_identity_gates(old_nodes, parsed.nodes)
