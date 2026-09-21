"""分总成在不同 L0 下叶子构成必须一致。"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.exceptions.base import BusinessException
from app.parsers.bom.bom_parser import parse_bom_excel
from app.parsers.bom.models import BomParsedNode
from app.services.bom.bom.rules.subassembly_consistency import (
    validate_subassembly_consistency,
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
    qty: Decimal | None = Decimal("1"),
    qty_unit: str = "pcs",
    weld_info: str | None = None,
    source_row: int | None = None,
) -> BomParsedNode:
    return BomParsedNode(
        level=level,
        parent_index=parent_index,
        sort_no=sort_no,
        part_number=part_number,
        qty=qty,
        qty_unit=qty_unit,
        weld_info=weld_info,
        source_row=source_row,
        node_role="structure" if level == 1 else "make",
    )


def test_same_subassembly_under_two_l0_with_same_leaves_passes() -> None:
    nodes = [
        _node(level=0, part_number="L0-A", parent_index=None, sort_no=1, source_row=10),
        _node(
            level=1,
            part_number="502007710AA-1",
            parent_index=0,
            sort_no=2,
            weld_info="CO2:2",
            source_row=11,
        ),
        _node(
            level=2,
            part_number="LEAF-A",
            parent_index=1,
            sort_no=3,
            qty=Decimal("1"),
            source_row=12,
        ),
        _node(
            level=2,
            part_number="LEAF-B",
            parent_index=1,
            sort_no=4,
            qty=Decimal("2"),
            source_row=13,
        ),
        _node(level=0, part_number="L0-B", parent_index=None, sort_no=5, source_row=20),
        _node(
            level=1,
            part_number="502007710AA-1",
            parent_index=4,
            sort_no=6,
            weld_info="CO2:2",
            source_row=21,
        ),
        _node(
            level=2,
            part_number="LEAF-B",
            parent_index=5,
            sort_no=7,
            qty=Decimal("2"),
            source_row=22,
        ),
        _node(
            level=2,
            part_number="LEAF-A",
            parent_index=5,
            sort_no=8,
            qty=Decimal("1"),
            source_row=23,
        ),
    ]
    validate_subassembly_consistency(nodes)


def test_same_subassembly_leaf_part_mismatch_raises() -> None:
    nodes = [
        _node(level=0, part_number="L0-A", parent_index=None, sort_no=1, source_row=10),
        _node(
            level=1,
            part_number="502007710AA-1",
            parent_index=0,
            sort_no=2,
            weld_info="CO2:2",
            source_row=11,
        ),
        _node(level=2, part_number="LEAF-A", parent_index=1, sort_no=3, source_row=12),
        _node(level=0, part_number="L0-B", parent_index=None, sort_no=4, source_row=20),
        _node(
            level=1,
            part_number="502007710AA-1",
            parent_index=3,
            sort_no=5,
            weld_info="CO2:2",
            source_row=21,
        ),
        _node(level=2, part_number="LEAF-X", parent_index=4, sort_no=6, source_row=22),
    ]
    with pytest.raises(BusinessException, match="构成不一致") as exc_info:
        validate_subassembly_consistency(nodes)
    message = str(exc_info.value)
    assert "502007710AA-1" in message
    assert "LEAF-A" in message
    assert "LEAF-X" in message


def test_same_subassembly_l2_vehicle_qty_mismatch_raises() -> None:
    """Excel 二级子件单车用量不同：1 板+3 螺母 vs 1 板+2 螺母。"""
    nodes = [
        _node(level=0, part_number="L0-A", parent_index=None, sort_no=1),
        _node(
            level=1,
            part_number="SUB-1",
            parent_index=0,
            sort_no=2,
            qty=Decimal("2"),
            weld_info="点焊:4",
        ),
        _node(level=2, part_number="PLATE-1", parent_index=1, sort_no=3, qty=Decimal("1")),
        _node(level=2, part_number="NUT-1", parent_index=1, sort_no=4, qty=Decimal("3")),
        _node(level=0, part_number="L0-B", parent_index=None, sort_no=5),
        _node(
            level=1,
            part_number="SUB-1",
            parent_index=4,
            sort_no=6,
            qty=Decimal("1"),
            weld_info="点焊:4",
        ),
        _node(level=2, part_number="PLATE-1", parent_index=5, sort_no=7, qty=Decimal("1")),
        _node(level=2, part_number="NUT-1", parent_index=5, sort_no=8, qty=Decimal("2")),
    ]
    with pytest.raises(BusinessException, match="单车用量") as exc_info:
        validate_subassembly_consistency(nodes)
    message = str(exc_info.value)
    assert "NUT-1×3" in message
    assert "NUT-1×2" in message
    assert "PLATE-1×1" in message


def test_same_subassembly_weld_mismatch_raises() -> None:
    nodes = [
        _node(level=0, part_number="L0-A", parent_index=None, sort_no=1),
        _node(
            level=1,
            part_number="SUB-1",
            parent_index=0,
            sort_no=2,
            weld_info="点焊:4",
        ),
        _node(level=2, part_number="LEAF-A", parent_index=1, sort_no=3),
        _node(level=0, part_number="L0-B", parent_index=None, sort_no=4),
        _node(
            level=1,
            part_number="SUB-1",
            parent_index=3,
            sort_no=5,
            weld_info="点焊:6",
        ),
        _node(level=2, part_number="LEAF-A", parent_index=4, sort_no=6),
    ]
    with pytest.raises(BusinessException, match="焊信"):
        validate_subassembly_consistency(nodes)


def test_same_part_as_subassembly_and_leaf_raises() -> None:
    nodes = [
        _node(level=0, part_number="L0-A", parent_index=None, sort_no=1, source_row=10),
        _node(
            level=1,
            part_number="SUB-1",
            parent_index=0,
            sort_no=2,
            weld_info="点焊:4",
            source_row=11,
        ),
        _node(level=2, part_number="LEAF-A", parent_index=1, sort_no=3, source_row=12),
        _node(level=0, part_number="L0-B", parent_index=None, sort_no=4, source_row=20),
        _node(
            level=1,
            part_number="SUB-1",
            parent_index=3,
            sort_no=5,
            weld_info="点焊:4",
            source_row=21,
        ),
    ]
    with pytest.raises(BusinessException, match="无二级子件"):
        validate_subassembly_consistency(nodes)


def test_same_l2_vehicle_qty_passes_even_if_parent_qty_differs() -> None:
    """L1 挂用量可以不同；二级单车用量按 Excel 原值相同即通过，不连乘。"""
    nodes = [
        _node(level=0, part_number="L0-A", parent_index=None, sort_no=1),
        _node(
            level=1,
            part_number="SUB-1",
            parent_index=0,
            sort_no=2,
            qty=Decimal("1"),
            weld_info="点焊:4",
        ),
        _node(level=2, part_number="LEAF-A", parent_index=1, sort_no=3, qty=Decimal("1")),
        _node(level=2, part_number="NUT-1", parent_index=1, sort_no=4, qty=Decimal("3")),
        _node(level=0, part_number="L0-B", parent_index=None, sort_no=5),
        _node(
            level=1,
            part_number="SUB-1",
            parent_index=4,
            sort_no=6,
            qty=Decimal("3"),
            weld_info="点焊:4",
        ),
        _node(level=2, part_number="LEAF-A", parent_index=5, sort_no=7, qty=Decimal("1")),
        _node(level=2, part_number="NUT-1", parent_index=5, sort_no=8, qty=Decimal("3")),
    ]
    validate_subassembly_consistency(nodes)


def test_l1_stamping_leaves_with_same_part_are_not_checked() -> None:
    nodes = [
        _node(level=0, part_number="L0-A", parent_index=None, sort_no=1),
        _node(level=1, part_number="STAMP-1", parent_index=0, sort_no=2),
        _node(level=0, part_number="L0-B", parent_index=None, sort_no=3),
        _node(level=1, part_number="STAMP-1", parent_index=2, sort_no=4),
    ]
    validate_subassembly_consistency(nodes)


@_skip_t13j_bom
def test_t13j_wuhu_material_list_flags_weld_mismatch() -> None:
    """芜湖 T13J D/09 材料清单：17 个重复分总成里仅 502007773AA 焊信不一致。"""
    parsed = parse_bom_excel(_T13J_BOM)
    assert parsed.meta.vehicle_model == "T13J"
    assert parsed.meta.bom_version == "D/09"
    l1_count = sum(1 for node in parsed.nodes if int(node.level) == 1)
    l2_count = sum(1 for node in parsed.nodes if int(node.level) == 2)
    assert l1_count == 205
    assert l2_count == 108

    with pytest.raises(BusinessException, match="构成不一致") as exc_info:
        validate_subassembly_consistency(parsed.nodes)

    message = exc_info.value.message
    assert "502007773AA" in message
    assert "凸焊：1" in message
    assert "凸焊：4" in message
    assert message.count("分总成 ") == 1
    assert "第 66 行" in message
    assert "第 80 行" in message
    assert "第 182 行" in message
    assert "第 196 行" in message
    assert "二级子件单车用量" in message
    assert "502007774AA×1" in message
    assert "N0111931×1" in message
