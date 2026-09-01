"""BOM 分总成构成一致性：同一零件号在不同 L0 下二级子件必须相同。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.exceptions.base import BusinessException
from app.parsers.bom.models import BomParsedNode


def _text(value: str | None) -> str:
    return (value or "").strip()


def _part_key(value: str | None) -> str:
    return _text(value).upper()


def _vehicle_qty_token(qty: Decimal | None) -> str:
    """Excel「二级子件单车用量」落在节点 qty，不连乘父级用量。"""
    if qty is None:
        return ""
    return format(qty.normalize(), "f")


def _children_map(nodes: list[BomParsedNode]) -> dict[int, list[int]]:
    mapping: dict[int, list[int]] = defaultdict(list)
    for index, node in enumerate(nodes):
        if node.parent_index is None:
            continue
        mapping[node.parent_index].append(index)
    return mapping


def _l2_child_indices(root_index: int, children_map: dict[int, list[int]]) -> list[int]:
    """分总成的直接子件（材料清单里的二级行），不含分总成本身。"""
    return list(children_map.get(root_index, ()))


def _l2_signature(
    root_index: int,
    nodes: list[BomParsedNode],
    children_map: dict[int, list[int]],
) -> tuple[tuple[str, str], ...]:
    items: list[tuple[str, str]] = []
    for index in _l2_child_indices(root_index, children_map):
        child = nodes[index]
        items.append(
            (
                _part_key(child.part_number),
                _vehicle_qty_token(child.qty),
            )
        )
    return tuple(sorted(items))


def _instance_signature(
    index: int,
    nodes: list[BomParsedNode],
    children_map: dict[int, list[int]],
) -> tuple[str, tuple[tuple[str, str], ...]]:
    node = nodes[index]
    return (_text(node.weld_info), _l2_signature(index, nodes, children_map))


def _row_label(node: BomParsedNode) -> str:
    if node.source_row is not None:
        return f"第 {node.source_row} 行"
    return f"序号 {node.sort_no}"


def _format_l2_children(
    root_index: int,
    nodes: list[BomParsedNode],
    children_map: dict[int, list[int]],
) -> str:
    child_indices = _l2_child_indices(root_index, children_map)
    if not child_indices:
        return "无二级子件"
    parts: list[str] = []
    for index in sorted(child_indices, key=lambda i: _part_key(nodes[i].part_number)):
        child = nodes[index]
        part_number = _text(child.part_number) or "-"
        qty_text = _vehicle_qty_token(child.qty) or "-"
        parts.append(f"{part_number}×{qty_text}")
    return "、".join(parts)


def _format_weld(weld_info: str | None) -> str:
    text = _text(weld_info)
    if not text:
        return "空"
    if len(text) > 80:
        return f"{text[:80]}…"
    return text


def _conflict_block(
    part_number: str,
    indices: list[int],
    nodes: list[BomParsedNode],
    children_map: dict[int, list[int]],
) -> str:
    lines = [f"分总成 {part_number}："]
    for index in indices:
        node = nodes[index]
        lines.append(
            f"- Excel {_row_label(node)}：焊信「{_format_weld(node.weld_info)}」，"
            f"二级子件单车用量 {_format_l2_children(index, nodes, children_map)}"
        )
    return "\n".join(lines)


def validate_subassembly_consistency(nodes: list[BomParsedNode]) -> None:
    """
    同一分总成可挂在多个 L0 下，但焊信与二级子件构成必须相同。

    构成取材料清单原值：二级行的零件号 +「二级子件单车用量」（节点 qty）。
    不按总成/一级用量连乘。L1 自身挂在父总成下的用量不参与比对。

    分总成 = level=1 且至少有一处出现子件。同零件号的其它 L1（含无子件）一并比对。
    """
    children_map = _children_map(nodes)
    by_part: dict[str, list[int]] = defaultdict(list)
    for index, node in enumerate(nodes):
        if int(node.level) != 1:
            continue
        part_number = _part_key(node.part_number)
        if not part_number:
            continue
        by_part[part_number].append(index)

    conflicts: list[str] = []
    for part_number, indices in by_part.items():
        has_subassembly = any(children_map.get(index) for index in indices)
        if not has_subassembly or len(indices) < 2:
            continue
        signatures = {_instance_signature(index, nodes, children_map) for index in indices}
        if len(signatures) <= 1:
            continue
        conflicts.append(_conflict_block(part_number, indices, nodes, children_map))

    if not conflicts:
        return

    detail = "\n".join(conflicts)
    raise BusinessException(
        "同一分总成在不同总成下的构成不一致"
        "（焊信与二级子件零件号、单车用量必须相同，用量取自 Excel，不连乘）：\n"
        f"{detail}"
    )
