"""
BOM 树节点解析

三级稀疏表：总成(L0) / 一级(L1) / 二级(L2)，合并单元格按向下继承处理。
"""

from __future__ import annotations

from typing import Any


from decimal import Decimal

from app.parsers.bom.models import BomParsedNode
from app.parsers.bom.value_parser import (
    cell_value,
    parse_qty,
    parse_seq_no,
    parse_thickness,
    to_decimal,
    to_text,
)


def infer_node_role(
    level: int,
    *,
    has_children_hint: bool,
    thickness_text: str | None,
    thickness_mm: Decimal | None,
    qty_unit: str,
    material: str | None,
) -> str:
    """
    推断 BOM 节点角色（冲焊件供应商域）。

    角色仅限：supply / structure / make / buy / consumable。
    make = 自制冲压件；不含电子/电气品类。
    零件名称含「电机」「线束」等字样不改变角色判定。
    """
    if level == 0:
        return "supply"
    if has_children_hint:
        return "structure"
    if qty_unit == "mm":
        return "consumable"
    if thickness_mm is not None:
        return "make"
    if thickness_text:
        upper = thickness_text.upper()
        if upper.startswith("M") or "X" in upper:
            return "buy"
    if material and any(key in material.upper() for key in ("TEROSON", "胶")):
        return "consumable"
    if material:
        return "make"
    return "buy"


def parse_bom_nodes(ws: Any) -> tuple[list[BomParsedNode], dict[int, int], dict[int, int]]:
    """
    解析树节点，并建立「Excel 行 → 节点」归属，供图示锚点匹配。

    终止规则：
    - 出现新总成（L0）时，A 列必须是数字序号；否则视为表尾，停止解析
    - A 列有内容但不是数字时，同样停止（序号区结束）

    单件图示（P 列）归属规则：
    - 有 L2：归当前 L2（含合并单元格续行）
    - 无 L2：归当前 L1（P 列即一级零件图）
    """
    nodes: list[BomParsedNode] = []
    current_l0_index: int | None = None
    current_l1_index: int | None = None
    current_l2_index: int | None = None
    sort_counter = 0
    row_l0: dict[int, int] = {}
    row_part_sketch: dict[int, int] = {}  # P 列单件图归属：L2 优先，否则 L1
    seen_data_row = False

    header_row = _find_header_row(ws)

    for row in range(header_row + 1, ws.max_row + 1):
        seq_raw = cell_value(ws, row, 1)
        seq_no = parse_seq_no(seq_raw)
        seq_text = to_text(seq_raw)

        # A 列有内容但不是数字 → 表尾（如「制表」「备注」），停止
        if seq_text is not None and seq_no is None:
            break

        asm_internal = to_text(cell_value(ws, row, 2))
        asm_part = to_text(cell_value(ws, row, 3))
        asm_name = to_text(cell_value(ws, row, 4))
        asm_qty_raw = cell_value(ws, row, 6)
        asm_weld = to_text(cell_value(ws, row, 7))

        l1_internal = to_text(cell_value(ws, row, 8))
        l1_part = to_text(cell_value(ws, row, 9))
        l1_name = to_text(cell_value(ws, row, 10))
        l1_qty_raw = cell_value(ws, row, 11)
        l1_weld = to_text(cell_value(ws, row, 12))

        l2_internal = to_text(cell_value(ws, row, 13))
        l2_part = to_text(cell_value(ws, row, 14))
        l2_name = to_text(cell_value(ws, row, 15))
        l2_qty_raw = cell_value(ws, row, 17)

        material = to_text(cell_value(ws, row, 18))
        thickness_mm, thickness_text = parse_thickness(cell_value(ws, row, 19))
        material_mill = to_text(cell_value(ws, row, 20))
        part_weight = to_decimal(cell_value(ws, row, 21))
        gauge_developed = to_text(cell_value(ws, row, 22))
        remark = to_text(cell_value(ws, row, 23))

        has_asm = bool(asm_part or asm_internal)
        has_l1 = bool(l1_part or l1_internal)
        has_l2 = bool(l2_part or l2_internal)

        # 新总成必须带数字序号；已进入数据区后 A 空却出现总成列 → 表尾
        if has_asm and seq_no is None:
            if seen_data_row:
                break
            # 表头后尚未出现有效数据时跳过噪声行
            continue

        deepest_index: int | None = None

        if has_asm or has_l1 or has_l2:
            seen_data_row = True
            if has_asm:
                sort_counter += 1
                qty, qty_unit, qty_text = parse_qty(asm_qty_raw)
                node = BomParsedNode(
                    level=0,
                    parent_index=None,
                    sort_no=sort_counter,
                    seq_no=seq_no,
                    internal_number=asm_internal,
                    part_number=asm_part or asm_internal or f"ASM-{sort_counter}",
                    part_name=asm_name,
                    qty=qty if qty is not None else Decimal("1"),
                    qty_unit=qty_unit,
                    qty_text=qty_text,
                    node_role="supply",
                    is_supply_unit=True,
                    weld_info=asm_weld,
                    source_row=row,
                )
                current_l0_index = len(nodes)
                current_l1_index = None
                current_l2_index = None
                nodes.append(node)
                deepest_index = current_l0_index

            if has_l1:
                if current_l0_index is None:
                    sort_counter += 1
                    placeholder = BomParsedNode(
                        level=0,
                        parent_index=None,
                        sort_no=sort_counter,
                        part_number=f"UNKNOWN-ASM-{sort_counter}",
                        part_name="未识别总成",
                        qty=Decimal("1"),
                        node_role="supply",
                        is_supply_unit=True,
                        source_row=row,
                    )
                    current_l0_index = len(nodes)
                    nodes.append(placeholder)

                sort_counter += 1
                qty, qty_unit, qty_text = parse_qty(l1_qty_raw)
                node = BomParsedNode(
                    level=1,
                    parent_index=current_l0_index,
                    sort_no=sort_counter,
                    internal_number=l1_internal,
                    part_number=l1_part or l1_internal or f"L1-{sort_counter}",
                    part_name=l1_name,
                    qty=qty if qty is not None else Decimal("1"),
                    qty_unit=qty_unit,
                    qty_text=qty_text,
                    node_role="make",
                    weld_info=l1_weld,
                    source_row=row,
                )
                current_l1_index = len(nodes)
                current_l2_index = None  # 新一级开始，清空二级上下文
                nodes.append(node)
                deepest_index = current_l1_index

            if has_l2:
                if current_l1_index is not None:
                    sort_counter += 1
                    qty, qty_unit, qty_text = parse_qty(l2_qty_raw)
                    node = BomParsedNode(
                        level=2,
                        parent_index=current_l1_index,
                        sort_no=sort_counter,
                        internal_number=l2_internal,
                        part_number=l2_part or l2_internal or f"L2-{sort_counter}",
                        part_name=l2_name,
                        qty=qty if qty is not None else Decimal("1"),
                        qty_unit=qty_unit,
                        qty_text=qty_text,
                        node_role="make",
                        source_row=row,
                    )
                    current_l2_index = len(nodes)
                    deepest_index = current_l2_index
                    nodes.append(node)
                    nodes[current_l1_index].node_role = "structure"

            # 材料属性落到本行最深节点（通常不是 L0）
            if deepest_index is not None and deepest_index != current_l0_index:
                target = nodes[deepest_index]
                if material:
                    target.material = material
                if thickness_text:
                    target.thickness_text = thickness_text
                if thickness_mm is not None:
                    target.thickness_mm = thickness_mm
                if material_mill:
                    target.material_mill = material_mill
                if part_weight is not None:
                    target.part_weight = part_weight
                if gauge_developed:
                    target.gauge_developed = gauge_developed
                if remark:
                    target.remark = remark

                if target.level > 0 and target.node_role != "structure":
                    target.node_role = infer_node_role(
                        target.level,
                        has_children_hint=False,
                        thickness_text=target.thickness_text,
                        thickness_mm=target.thickness_mm,
                        qty_unit=target.qty_unit,
                        material=target.material,
                    )

        # 行归属：供图示锚点匹配（含空行/合并续行，继承当前上下文）
        if current_l0_index is not None:
            row_l0[row] = current_l0_index
        # P 列单件图：有 L2 归 L2，无 L2 归 L1
        if current_l2_index is not None:
            row_part_sketch[row] = current_l2_index
        elif current_l1_index is not None:
            row_part_sketch[row] = current_l1_index

    _finalize_structure_roles(nodes)
    return nodes, row_l0, row_part_sketch


def _find_header_row(ws: Any) -> int:
    """找到表头行（含「总成」与「一级」）。"""
    header_row = 4
    for row in range(1, min(15, ws.max_row + 1)):
        joined = "".join(str(cell_value(ws, row, c) or "") for c in range(1, 12))
        if "总成" in joined and "一级" in joined:
            return row
    return header_row


def _finalize_structure_roles(nodes: list[BomParsedNode]) -> None:
    """有子节点的非 L0 一律标记为 structure。"""
    children_count = [0] * len(nodes)
    for node in nodes:
        if node.parent_index is not None:
            children_count[node.parent_index] += 1
    for index, node in enumerate(nodes):
        if node.level > 0 and children_count[index] > 0:
            node.node_role = "structure"
            node.is_supply_unit = False
