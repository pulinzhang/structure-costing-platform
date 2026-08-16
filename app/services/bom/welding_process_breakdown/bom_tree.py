"""
BOM 树辅助（焊接工艺拆解生成用）

只处理邻接表导航与节点状态标注，不写库。
"""

from __future__ import annotations

from collections import defaultdict

from app.models.bom import BomNode


def build_children_map(bom_nodes: list[BomNode]) -> dict[int | None, list[BomNode]]:
    """parent_id → 直接子节点列表。"""
    children_map: dict[int | None, list[BomNode]] = defaultdict(list)
    for node in bom_nodes:
        children_map[node.parent_id].append(node)
    return children_map


def index_nodes_by_id(bom_nodes: list[BomNode]) -> dict[int, BomNode]:
    return {node.id: node for node in bom_nodes}


def resolve_supply_root(node: BomNode, by_id: dict[int, BomNode]) -> BomNode:
    """沿 parent 上溯到供货总成（L0）。"""
    current = node
    while current.parent_id is not None:
        parent = by_id.get(current.parent_id)
        if parent is None:
            break
        current = parent
    return current


def annotate_parse_status(
    *,
    level: int,
    has_children: bool,
    base_parse_status: str,
) -> tuple[str, str | None]:
    """
    在原文拆解状态之上叠加业务标注。

    返回 (parse_status, qa_note)。
    - L≥2 出现焊接信息 → anomaly（结构异常）
    - L0 无有效工艺：保留 unparsed/partial，备注提示计费异常；
      筛选用 process_line_count=0，不把 anomaly 叠成第二套信号
    """
    if level >= 2:
        return "anomaly", "末级节点出现焊接信息，异常"

    notes: list[str] = []
    if not has_children and level == 0:
        notes.append("供货总成无下级子件（退化 L0）")
    if level == 0 and base_parse_status in ("unparsed", "partial"):
        notes.append("L0 无有效工艺明细（计费异常）")

    return base_parse_status, ("；".join(notes) if notes else None)
