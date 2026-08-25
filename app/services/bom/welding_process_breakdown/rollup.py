"""
父子工艺 rollup 标记

规则（供货总成口径）：
- L0.process_qty(token) == Σ(L1.process_qty × L1.assembly_qty)
  → 子行 rollup_flag = rolled_in_parent
- 子级有、父级无同名 token
  → 子行 rollup_flag = orphan_child
- 其余保持 own（调用方须先将待算行重置为 own）
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.models.bom import BomNode, BomWeldingProcessBreakdownLine, BomWeldingProcessBreakdownNode


def apply_rollup_flags(
    breakdown_nodes: list[BomWeldingProcessBreakdownNode],
    source_to_breakdown: dict[int, BomWeldingProcessBreakdownNode],
    children_map: dict[int | None, list[BomNode]],
) -> None:
    """就地修改明细行的 rollup 标记（调用方负责 flush/commit）。"""
    for node in breakdown_nodes:
        if node.level != 0 or node.source_node_id is None:
            continue

        parent_tokens = {line.process_token: line.process_qty for line in node.lines}
        child_bom_nodes = children_map.get(node.source_node_id, [])
        child_token_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        child_lines_by_token: dict[str, list[BomWeldingProcessBreakdownLine]] = defaultdict(list)

        for child_bom in child_bom_nodes:
            child_breakdown = source_to_breakdown.get(child_bom.id)
            if not child_breakdown:
                continue
            for line in child_breakdown.lines:
                contrib = line.process_qty * child_breakdown.assembly_qty
                child_token_totals[line.process_token] += contrib
                child_lines_by_token[line.process_token].append(line)

        for token, total in child_token_totals.items():
            parent_qty = parent_tokens.get(token)
            if parent_qty is not None and parent_qty == total:
                for line in child_lines_by_token[token]:
                    line.rollup_flag = "rolled_in_parent"
            elif parent_qty is None:
                for line in child_lines_by_token[token]:
                    line.rollup_flag = "orphan_child"
