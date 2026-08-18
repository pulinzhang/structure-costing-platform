"""
将 BOM 图示锚点归属到已解析节点。

图示归属：
- E 列总成图示 → L0
- P 列单件图示 → 有 L2 归 L2；无 L2 时归 L1（一级零件图）
"""

from __future__ import annotations

from app.parsers.bom.image_extractor import (
    ASSEMBLY_SKETCH_COL,
    PART_SKETCH_COL,
    extract_bom_images,
)
from app.parsers.bom.models import BomParsedNode


def assign_sketch_images(
    file_bytes: bytes,
    nodes: list[BomParsedNode],
    row_l0: dict[int, int],
    row_part_sketch: dict[int, int],
) -> int:
    anchors = extract_bom_images(file_bytes)
    assigned = 0
    for anchor in anchors:
        node_index: int | None = None
        if anchor.col_0idx == ASSEMBLY_SKETCH_COL:
            node_index = row_l0.get(anchor.excel_row)
        elif anchor.col_0idx == PART_SKETCH_COL:
            node_index = row_part_sketch.get(anchor.excel_row)

        if node_index is None or node_index < 0 or node_index >= len(nodes):
            continue
        # 同节点多图保留最后一张（与冲压一致）
        nodes[node_index].sketch_bytes = anchor.png_bytes
        assigned += 1
    return assigned
