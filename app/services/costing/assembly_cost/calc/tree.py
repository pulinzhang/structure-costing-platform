"""总成月核价 rollup：叶子取价与树遍历。"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from app.common.bom.node_order import bom_node_order_from
from app.services.costing.assembly_cost.calc.rollup_models import RollupBomNode


def base_part_number_before_dash(part_number: str) -> str | None:
    if "-" not in part_number:
        return None
    base = part_number.split("-", 1)[0].strip()
    return base or None


def lookup_leaf_price(
    part_number: str,
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
    conflicted_part_numbers: frozenset[str] | None = None,
) -> tuple[Literal["stamping", "annual"] | None, Decimal | None, str | None]:
    """返回 (source, unit, match_hint)。"""
    conflicted = conflicted_part_numbers or frozenset()
    if part_number in conflicted:
        return None, None, "multi_supplier_unit_cost"
    if part_number in stamping_prices:
        return "stamping", stamping_prices[part_number], None
    if part_number in annual_prices:
        return "annual", annual_prices[part_number], None
    base = base_part_number_before_dash(part_number)
    if base is not None and base in conflicted:
        return None, None, "multi_supplier_unit_cost"
    if base is not None and base in stamping_prices:
        return "stamping", stamping_prices[base], f"dash_fallback:{base}"
    return None, None, None


def supply_type_of(node: RollupBomNode) -> str | None:
    return node.supply_type or node.node_role


def node_qty(node: RollupBomNode) -> Decimal:
    return node.qty if node.qty is not None else Decimal("1")


def sorted_children(
    children_by_parent: dict[int | None, list[RollupBomNode]],
    node_id: int | None,
) -> list[RollupBomNode]:
    kids = children_by_parent.get(node_id, [])
    return sorted(kids, key=bom_node_order_from)


def collect_descendants(
    children_by_parent: dict[int | None, list[RollupBomNode]],
    node_id: int,
) -> list[RollupBomNode]:
    found: list[RollupBomNode] = []
    stack = list(sorted_children(children_by_parent, node_id))
    while stack:
        current = stack.pop(0)
        found.append(current)
        stack.extend(sorted_children(children_by_parent, current.id))
    return found


def path_qty_from_root_child(
    children_by_parent: dict[int | None, list[RollupBomNode]],
    by_id: dict[int, RollupBomNode],
    root_id: int,
    target_id: int,
) -> Decimal:
    """从核价根的直接子走到 target 的 qty 连乘（不含根 qty）。"""
    chain: list[RollupBomNode] = []
    current_id: int | None = target_id
    while current_id is not None and current_id != root_id:
        node = by_id.get(current_id)
        if node is None:
            break
        chain.append(node)
        current_id = node.parent_id
    product = Decimal("1")
    for node in reversed(chain):
        product *= node_qty(node)
    return product


def index_nodes(
    root: RollupBomNode,
    children_by_parent: dict[int | None, list[RollupBomNode]],
    nodes_by_id: dict[int, RollupBomNode] | None,
) -> dict[int, RollupBomNode]:
    by_id = nodes_by_id or {}
    if not by_id:
        for kids in children_by_parent.values():
            for node in kids:
                by_id[node.id] = node
        by_id[root.id] = root
    return by_id
