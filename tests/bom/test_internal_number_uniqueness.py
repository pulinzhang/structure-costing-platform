"""有内部号的物料必须一物一码。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.exceptions.base import BusinessException
from app.parsers.bom.bom_parser import parse_bom_excel
from app.parsers.bom.models import BomParsedNode
from app.services.bom.bom.rules.internal_number_uniqueness import (
    validate_internal_number_uniqueness,
)

_T13J_BOM = (
    Path(__file__).resolve().parents[2]
    / "excel_sample"
    / "T13J"
    / "T13J项目车身件材料清单 (1).xlsx"
)
_skip_t13j_bom = pytest.mark.skipif(
    not _T13J_BOM.is_file(),
    reason="样本 Excel 未放入 excel_sample/T13J",
)


def _node(
    *,
    level: int,
    part_number: str,
    parent_index: int | None,
    sort_no: int,
    internal_number: str | None = None,
    part_name: str | None = None,
    source_row: int | None = None,
) -> BomParsedNode:
    return BomParsedNode(
        level=level,
        parent_index=parent_index,
        sort_no=sort_no,
        part_number=part_number,
        internal_number=internal_number,
        part_name=part_name,
        source_row=source_row,
        node_role="structure" if level == 1 else "make",
    )


def test_same_part_same_internal_under_two_l0_passes() -> None:
    nodes = [
        _node(level=0, part_number="L0-A", parent_index=None, sort_no=1, internal_number="ACA1"),
        _node(
            level=1,
            part_number="502007791AA",
            parent_index=0,
            sort_no=2,
            internal_number="ACA688N01",
            source_row=78,
        ),
        _node(level=0, part_number="L0-B", parent_index=None, sort_no=3, internal_number="ACA2"),
        _node(
            level=1,
            part_number="502007791AA",
            parent_index=2,
            sort_no=4,
            internal_number="ACA688N01",
            source_row=194,
        ),
    ]
    validate_internal_number_uniqueness(nodes)


def test_empty_internal_does_not_conflict_with_coded_row() -> None:
    nodes = [
        _node(
            level=1,
            part_number="501007031AA",
            parent_index=None,
            sort_no=1,
            internal_number="ACA613001",
        ),
        _node(
            level=2,
            part_number="501007031AA",
            parent_index=0,
            sort_no=2,
            internal_number=None,
        ),
    ]
    validate_internal_number_uniqueness(nodes)


def test_same_part_different_internal_raises() -> None:
    nodes = [
        _node(level=0, part_number="L0-A", parent_index=None, sort_no=1, internal_number="ACA688"),
        _node(
            level=1,
            part_number="502007791AA",
            parent_index=0,
            sort_no=2,
            internal_number="ACA688N01A",
            part_name="右B柱内板本体总成",
            source_row=78,
        ),
        _node(level=0, part_number="L0-B", parent_index=None, sort_no=3, internal_number="CA0009"),
        _node(
            level=1,
            part_number="502007791AA",
            parent_index=2,
            sort_no=4,
            internal_number="ACA688N01",
            part_name="右B柱内板本体总成",
            source_row=194,
        ),
    ]
    with pytest.raises(BusinessException, match="一物一码") as exc_info:
        validate_internal_number_uniqueness(nodes)
    message = str(exc_info.value)
    assert "502007791AA" in message
    assert "ACA688N01A" in message
    assert "ACA688N01" in message
    assert "第 78 行" in message
    assert "第 194 行" in message


def test_same_internal_different_part_raises() -> None:
    nodes = [
        _node(
            level=1,
            part_number="P-A",
            parent_index=None,
            sort_no=1,
            internal_number="ERP001",
            source_row=10,
        ),
        _node(
            level=1,
            part_number="P-B",
            parent_index=None,
            sort_no=2,
            internal_number="ERP001",
            source_row=11,
        ),
    ]
    with pytest.raises(BusinessException, match="内部号 ERP001 对应多个零件号") as exc_info:
        validate_internal_number_uniqueness(nodes)
    message = str(exc_info.value)
    assert "P-A" in message
    assert "P-B" in message


def test_internal_and_part_keys_ignore_case_and_spaces() -> None:
    nodes = [
        _node(
            level=1,
            part_number=" 502007791aa ",
            parent_index=None,
            sort_no=1,
            internal_number=" aca688n01a ",
            source_row=1,
        ),
        _node(
            level=1,
            part_number="502007791AA",
            parent_index=None,
            sort_no=2,
            internal_number="ACA688N01",
            source_row=2,
        ),
    ]
    with pytest.raises(BusinessException, match="对应多个内部号"):
        validate_internal_number_uniqueness(nodes)


@_skip_t13j_bom
def test_t13j_wuhu_material_list_flags_internal_number_clash() -> None:
    parsed = parse_bom_excel(_T13J_BOM)
    try:
        validate_internal_number_uniqueness(parsed.nodes)
    except BusinessException as exc_info:
        message = exc_info.message
        assert "一物一码" in message
        assert "502007791AA" in message
        assert "ACA688N01A" in message
        assert "ACA688N01" in message
        assert "第 78 行" in message
        assert "第 194 行" in message
        return
    pytest.skip("样本材料清单已无内部号冲突")
