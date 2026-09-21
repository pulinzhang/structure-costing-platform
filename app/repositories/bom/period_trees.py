"""BOM 树期：只认 L0 树根，再收整棵子树。

四年后改期口径只改这里：
- 月命中 → ``nodes_in_as_of_trees``
- 年交集 → ``nodes_in_year_overlap_trees``
- 树根版本字 → ``nodes_for_l0_version`` / ``node_ids_for_l0_version``
- 任意节点找树根 → ``tree_root_of``

禁止用 L1/L2 本行生失效筛半棵树。树根判定：``level == 0``。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from app.common.bom.node_order import bom_node_order_from
from app.common.period import is_in_period, overlaps_year
from app.models.bom import BomNode


def is_tree_root(node: BomNode) -> bool:
    return int(node.level) == 0


def collect_root_subtrees(
    all_nodes: Sequence[BomNode],
    *,
    root_hits: Sequence[BomNode],
) -> list[BomNode]:
    """从已命中的树根收下整棵子树；子孙本行生失效不再筛。"""
    children: dict[int | None, list[BomNode]] = defaultdict(list)
    for node in all_nodes:
        children[node.parent_id].append(node)
    kept: list[BomNode] = []
    stack = list(root_hits)
    while stack:
        current = stack.pop()
        kept.append(current)
        stack.extend(children.get(current.id, []))
    kept.sort(key=bom_node_order_from)
    return kept


def nodes_in_as_of_trees(
    all_nodes: Sequence[BomNode],
    *,
    as_of_year: int,
    as_of_month: int,
) -> list[BomNode]:
    roots = [
        node
        for node in all_nodes
        if is_tree_root(node)
        and is_in_period(
            effective_year=node.effective_year,
            effective_month=node.effective_month,
            expiry_year=node.expiry_year,
            expiry_month=node.expiry_month,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )
    ]
    return collect_root_subtrees(all_nodes, root_hits=roots)


def nodes_in_year_overlap_trees(
    all_nodes: Sequence[BomNode],
    *,
    year: int,
) -> list[BomNode]:
    roots = [
        node
        for node in all_nodes
        if is_tree_root(node)
        and overlaps_year(
            effective_year=node.effective_year,
            effective_month=node.effective_month,
            expiry_year=node.expiry_year,
            expiry_month=node.expiry_month,
            year=year,
        )
    ]
    return collect_root_subtrees(all_nodes, root_hits=roots)


def nodes_for_l0_version(
    all_nodes: Sequence[BomNode],
    *,
    bom_version: str,
) -> list[BomNode]:
    """树根版本字命中的整棵子树。版本只问 L0。"""
    wanted = (bom_version or "").strip()
    roots = [
        node
        for node in all_nodes
        if is_tree_root(node) and (node.bom_version or "").strip() == wanted
    ]
    return collect_root_subtrees(all_nodes, root_hits=roots)


def node_ids_for_l0_version(
    all_nodes: Sequence[BomNode],
    *,
    bom_version: str,
) -> set[int]:
    return {int(node.id) for node in nodes_for_l0_version(all_nodes, bom_version=bom_version)}


def tree_root_of(node: BomNode, by_id: dict[int, BomNode]) -> BomNode:
    current = node
    seen: set[int] = set()
    while current.parent_id is not None and current.parent_id in by_id:
        node_id = int(current.id)
        if node_id in seen:
            break
        seen.add(node_id)
        current = by_id[current.parent_id]
    return current
