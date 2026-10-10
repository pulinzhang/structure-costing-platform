"""BOM 零件号到 L0 总成映射。"""

from app.models.bom import BomNode


def build_part_to_l0_map(nodes: list[BomNode]) -> dict[str, str]:
    """
    零件号 → L0 供货总成零件号。
    同一冲压件挂在多个总成下时，收集全部 L0，英文逗号分隔（去重、保序）。
    """
    by_id = {node.id: node for node in nodes}
    roots_by_part: dict[str, list[str]] = {}

    for node in nodes:
        part_number = (node.part_number or "").strip()
        if not part_number:
            continue
        current = node
        visited: set[int] = set()
        while current.parent_id is not None:
            if current.id in visited:
                break
            visited.add(current.id)
            parent = by_id.get(current.parent_id)
            if parent is None:
                break
            current = parent
        root_part = (current.part_number or "").strip()
        if not root_part:
            continue
        bucket = roots_by_part.setdefault(part_number, [])
        if root_part not in bucket:
            bucket.append(root_part)

    return {part_number: ",".join(roots) for part_number, roots in roots_by_part.items()}
