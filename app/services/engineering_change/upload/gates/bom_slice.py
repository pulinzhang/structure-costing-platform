"""从工程变更材料清单里切出一棵交货总成（不改 BOM Parser）。"""

from __future__ import annotations

from dataclasses import replace

from app.common.engineering_change_gates import EC_BOM_NEW_ROOT, quoted
from app.exceptions.base import BusinessException
from app.parsers.bom.bom_parser import BomParsedNode


def slice_bom_nodes_for_l0(nodes: list[BomParsedNode], l0_part_number: str) -> list[BomParsedNode]:
    """按 parent_index 取出指定 L0 及其子孙，并重排下标。"""
    target = (l0_part_number or "").strip()
    roots = [
        index
        for index, node in enumerate(nodes)
        if node.level == 0 and (node.part_number or "").strip() == target
    ]
    if len(roots) != 1:
        raise BusinessException(
            f"{EC_BOM_NEW_ROOT}：材料清单里交货总成 {quoted(target)} "
            f"出现 {len(roots)} 次，必须恰好一次。"
        )
    keep: set[int] = {roots[0]}
    pending = [roots[0]]
    while pending:
        parent = pending.pop()
        for index, node in enumerate(nodes):
            if index in keep:
                continue
            if node.parent_index == parent:
                keep.add(index)
                pending.append(index)
    old_to_new = {old: new for new, old in enumerate(sorted(keep))}
    sliced: list[BomParsedNode] = []
    for old in sorted(keep):
        node = nodes[old]
        parent_index = None if node.parent_index is None else old_to_new[node.parent_index]
        sliced.append(replace(node, parent_index=parent_index))
    return sliced
