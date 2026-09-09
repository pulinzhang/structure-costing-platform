"""节点单车用量：从所属 L0 沿树连乘 qty。"""

from __future__ import annotations

from decimal import Decimal

from app.models.bom.node import BomNode


def node_qty(node: BomNode) -> Decimal:
    return node.qty if node.qty is not None else Decimal("1")


def vehicle_qty_from_l0(node_id: int, nodes_by_id: dict[int, BomNode]) -> Decimal:
    product = Decimal("1")
    current_id: int | None = node_id
    seen: set[int] = set()
    while current_id is not None and current_id not in seen:
        seen.add(current_id)
        node = nodes_by_id.get(current_id)
        if node is None:
            break
        product *= node_qty(node)
        current_id = node.parent_id
    return product


def l0_node_of(node_id: int, nodes_by_id: dict[int, BomNode]) -> BomNode | None:
    current = nodes_by_id.get(node_id)
    seen: set[int] = set()
    while current is not None and current.parent_id is not None:
        if current.id in seen:
            break
        seen.add(current.id)
        parent = nodes_by_id.get(current.parent_id)
        if parent is None:
            break
        current = parent
    return current
