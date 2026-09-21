"""同 snapshot 节点列表上按 parent_id 收子树。"""

from app.models.bom import BomNode


def descendant_ids(rows: list[BomNode], roots: set[int]) -> set[int]:
    children_of: dict[int, list[int]] = {}
    for row in rows:
        if row.parent_id is None:
            continue
        children_of.setdefault(row.parent_id, []).append(row.id)
    keep = set(roots)
    stack = list(roots)
    while stack:
        current = stack.pop()
        for child_id in children_of.get(current, []):
            if child_id in keep:
                continue
            keep.add(child_id)
            stack.append(child_id)
    return keep


def collect_subtree(rows: list[BomNode], root_id: int) -> list[BomNode]:
    """含 root 的整棵子树。"""
    keep = descendant_ids(rows, {root_id})
    return [row for row in rows if row.id in keep]
