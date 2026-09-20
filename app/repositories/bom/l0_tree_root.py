"""所属 L0 树根：snapshot_id + L0 零件号 + level=0。

采购对象列表 JOIN 树根用这里。期/版本树范围：算法 ``period_trees``，对外 ``BomPeriodService``。
禁止 source 本行字、禁止 snapshot 头字。
"""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import and_
from sqlalchemy.orm import Query, Session, aliased

from app.models.bom import BomNode

T = TypeVar("T")


def join_l0_tree_root(
    query: Query[T],
    snapshot_id_col: Any,
    l0_part_number_col: Any,
) -> tuple[Query[T], type[BomNode]]:
    """INNER JOIN 所属树根。调用方再筛 tree_root.bom_version / 生失效。"""
    tree_root = aliased(BomNode)
    joined = query.join(
        tree_root,
        and_(
            tree_root.snapshot_id == snapshot_id_col,
            tree_root.part_number == l0_part_number_col,
            tree_root.level == 0,
        ),
    )
    return joined, tree_root


def map_l0_nodes(
    db: Session,
    snapshot_l0_keys: list[tuple[int, str]],
) -> dict[tuple[int, str], BomNode]:
    """(snapshot_id, l0_part_number) → 树根节点。"""
    if not snapshot_l0_keys:
        return {}
    wanted = set(snapshot_l0_keys)
    snapshot_ids = {snapshot_id for snapshot_id, _ in wanted}
    part_numbers = {part_number for _, part_number in wanted}
    rows = (
        db.query(BomNode)
        .filter(
            BomNode.snapshot_id.in_(snapshot_ids),
            BomNode.part_number.in_(part_numbers),
            BomNode.level == 0,
        )
        .all()
    )
    result: dict[tuple[int, str], BomNode] = {}
    for node in rows:
        key = (int(node.snapshot_id), str(node.part_number))
        if key in wanted:
            result[key] = node
    return result
