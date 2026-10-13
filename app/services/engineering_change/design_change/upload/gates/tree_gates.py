"""变更单与材料清单、旧树对齐：缺层/错层/卸件双信号/内部号、总成图与一级单件图示。"""

from __future__ import annotations

from collections.abc import Sequence

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_ADD_SUBASSEMBLY,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    EC_ADD_ALREADY_ON_TREE,
    EC_ADD_LEVEL1_LEAF,
    EC_ADD_LEVEL1_NUMBER,
    EC_ADD_SUBASSEMBLY_SET,
    EC_ASSEMBLY_SKETCH_REQUIRED,
    EC_CHANGE_ORDER_COLUMNS,
    EC_INTERNAL_REQUIRED,
    EC_NOT_INSTALL_CHILDREN,
    EC_NOT_INSTALL_SIGNAL,
    EC_PART_NOT_ON_TREE,
    EC_PART_SKETCH_REQUIRED,
    EC_QTY_CHANGED,
    EC_REVISE_FILE_CHAIN,
    NOT_INSTALL_REMARK,
    PART_LEVEL_ASSEMBLY,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
    PART_LEVEL_TO_BOM_LEVEL,
    is_not_install_row,
    quoted,
)
from app.exceptions.base import BusinessException
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import BomParsedNode
from app.parsers.engineering_change.design_change.change_order_parser import ChangeOrderRowParsed
from app.services.bom.bom.change_tree_plant.number_map import (
    added_part_row,
    parent_level1_renumber,
    part_installed_at_level,
)
from app.services.bom.bom.rules.internal_number_uniqueness import (
    validate_internal_number_uniqueness,
)


def validate_change_tree_gates(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    """一种改法自己看自己。完成停止不进。此件不装和增加分总成不互相核对。"""
    if change_order.change_type == CHANGE_TYPE_STOP:
        return
    file_l0 = [node for node in sliced_nodes if int(node.level) == 0]
    if file_l0 and is_not_install_row(
        file_l0[0].qty, file_l0[0].remark, part_number=file_l0[0].part_number
    ):
        raise BusinessException(
            f"{EC_CHANGE_ORDER_COLUMNS}：{quoted(file_l0[0].part_number)} "
            "整个总成不要用量 0 +「此件不装」。整个总成不再交请用完成停止。"
        )
    if change_order.change_type == CHANGE_TYPE_REVISE:
        _validate_revise(change_order, old_nodes, sliced_nodes)
        return
    if change_order.change_type == CHANGE_TYPE_NOT_INSTALL:
        _validate_not_install(change_order, old_nodes, sliced_nodes)
        return
    if change_order.change_type == CHANGE_TYPE_ADD_PART:
        _validate_add_part(change_order, old_nodes, sliced_nodes)
        return
    if change_order.change_type == CHANGE_TYPE_ADD_SUBASSEMBLY:
        _validate_add_subassembly(change_order, old_nodes, sliced_nodes)


def validate_identity_gates(
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    """交货总成、分总成内部号；总成图（合并总成一张即可）；一二级单件图示；本张清单一物一码。"""
    validate_internal_number_uniqueness(_nodes_for_uniqueness(sliced_nodes))
    l0_groups: dict[str, list[BomParsedNode]] = {}
    for node in sliced_nodes:
        if int(node.level) != 0:
            continue
        number = (node.part_number or "").strip()
        l0_groups.setdefault(number, []).append(node)
    for group in l0_groups.values():
        if not any(_has_internal(node.internal_number) for node in group):
            raise BusinessException(
                f"{EC_INTERNAL_REQUIRED}：交货总成 {quoted(group[0].part_number)} 必须有内部号。"
            )
        if not any(node.sketch_bytes for node in group):
            raise BusinessException(
                f"{EC_ASSEMBLY_SKETCH_REQUIRED}：交货总成 {quoted(group[0].part_number)} "
                "必须有总成图。同一总成合并多行时只需一张，请贴在「总成图示」列。"
            )
    for node in sliced_nodes:
        if int(node.level) != 1:
            continue
        if _file_has_children(sliced_nodes, node) and not _has_internal(node.internal_number):
            raise BusinessException(
                f"{EC_INTERNAL_REQUIRED}：分总成 {quoted(node.part_number)} 必须有内部号。"
            )
    old_numbers = {(node.part_number or "").strip() for node in old_nodes}
    for node in sliced_nodes:
        if not _needs_part_sketch(sliced_nodes, node, old_numbers):
            continue
        if node.sketch_bytes:
            continue
        level_label = PART_LEVEL_L2 if int(node.level) == 2 else PART_LEVEL_L1
        raise BusinessException(
            f"{EC_PART_SKETCH_REQUIRED}：{level_label}零件 {quoted(node.part_number)} 没有单件图示。"
            "请在车身件材料清单「单件图示」列贴图，或在冲压工艺确认表给出该零件简图。"
        )
    children_of: dict[int | None, list[BomNode]] = {}
    for old_node in old_nodes:
        children_of.setdefault(old_node.parent_id, []).append(old_node)
    for old_node in old_nodes:
        if int(old_node.level) == 0 and not _has_internal(old_node.internal_number):
            raise BusinessException(
                f"{EC_INTERNAL_REQUIRED}：投产总成 {quoted(old_node.part_number)} 必须有内部号。"
            )
        if (
            int(old_node.level) == 1
            and children_of.get(old_node.id)
            and not _has_internal(old_node.internal_number)
        ):
            raise BusinessException(
                f"{EC_INTERNAL_REQUIRED}：投产分总成 {quoted(old_node.part_number)} 必须有内部号。"
            )


def apply_process_sketches_to_bom_nodes(
    nodes: list[BomParsedNode],
    process_sketches: dict[str, bytes],
) -> None:
    """材料清单缺单件图示时，按零件号抄冲压工艺确认表简图（落到 BOM 节点，种树时写入 sketches 目录）。"""
    if not process_sketches:
        return
    for node in nodes:
        if node.sketch_bytes:
            continue
        if not _needs_part_sketch(nodes, node):
            continue
        payload = process_sketches.get((node.part_number or "").strip())
        if payload:
            node.sketch_bytes = payload


def _validate_revise(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    if change_order.part_level == PART_LEVEL_ASSEMBLY:
        return
    old_part = _require_old_part(change_order, old_nodes)
    after_number = (change_order.after_part_number or "").strip()
    file_part = _find_file_part(sliced_nodes, after_number)
    if file_part is None or int(file_part.level) != int(old_part.level):
        raise BusinessException(
            f"{EC_REVISE_FILE_CHAIN}：材料清单没有变更后零件 {quoted(after_number)}，"
            f"或层级不是{quoted(change_order.part_level)}。"
        )
    old_chain = _old_chain_up(old_nodes, old_part)
    file_chain = _file_chain_up(sliced_nodes, file_part)
    if len(old_chain) != len(file_chain):
        raise BusinessException(
            f"{EC_REVISE_FILE_CHAIN}：材料清单没有写出 {quoted(after_number)} 到交货总成的整条换号链。"
        )
    for old_node, file_node in zip(old_chain, file_chain, strict=True):
        if int(old_node.level) != int(file_node.level):
            raise BusinessException(
                f"{EC_REVISE_FILE_CHAIN}：材料清单 {quoted(file_node.part_number)} "
                f"层级与投产 {quoted(old_node.part_number)} 对不上。"
            )


def _validate_not_install(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    old_part = _require_old_part(change_order, old_nodes)
    number = (change_order.before_part_number or "").strip()
    if not _has_not_install_signal(sliced_nodes, number):
        raise BusinessException(
            f"{EC_NOT_INSTALL_SIGNAL}：材料清单里 {quoted(number)} "
            f"必须用量 0 且备注含「{NOT_INSTALL_REMARK}」。"
        )
    descendants = _old_descendants(old_nodes, old_part.id)
    if not descendants:
        return
    for child in descendants:
        child_number = (child.part_number or "").strip()
        if not _has_not_install_signal(sliced_nodes, child_number):
            raise BusinessException(
                f"{EC_NOT_INSTALL_CHILDREN}：{quoted(child_number)} 是不装件的下级，"
                f"材料清单也要用量 0 且备注含「{NOT_INSTALL_REMARK}」。"
            )


def _validate_add_subassembly(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: Sequence[BomParsedNode],
) -> None:
    """增加一套一级节点：这一级，再加至少两颗二级。只有一颗二级不收。"""
    after_number = (change_order.after_part_number or "").strip()
    if part_installed_at_level(
        old_nodes,
        after_number,
        PART_LEVEL_TO_BOM_LEVEL[PART_LEVEL_L1],
    ):
        raise BusinessException(
            f"{EC_ADD_ALREADY_ON_TREE}：{quoted(after_number)} 已是变更前总成上的一级，不能当增加分总成。"
        )
    file_part = _find_file_part(sliced_nodes, after_number)
    if file_part is None or int(file_part.level) != 1:
        raise BusinessException(
            f"{EC_REVISE_FILE_CHAIN}：材料清单没有 {quoted(after_number)}，或层级不是一级。"
        )
    if file_part.qty is None or file_part.qty <= 0:
        raise BusinessException(
            f"{EC_QTY_CHANGED}：分总成 {quoted(after_number)} 用量必须大于 0，现在是 {file_part.qty}。"
        )
    if not (file_part.internal_number or "").strip():
        raise BusinessException(
            f"{EC_INTERNAL_REQUIRED}：分总成 {quoted(after_number)} 必须有内部号。"
        )
    level2_count = len(_installed_level2_children(sliced_nodes, file_part))
    if level2_count < 2:
        raise BusinessException(
            f"{EC_ADD_SUBASSEMBLY_SET}：{quoted(after_number)} 下面现在是 {level2_count} 颗二级。"
            "一套要同时有这一级，和至少两颗二级。"
        )


def _validate_add_part(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    after_number = (change_order.after_part_number or "").strip()
    expected_level = PART_LEVEL_TO_BOM_LEVEL[change_order.part_level]
    if part_installed_at_level(old_nodes, after_number, expected_level):
        raise BusinessException(
            f"{EC_ADD_ALREADY_ON_TREE}：{quoted(after_number)} 已是变更前总成上的{change_order.part_level}，"
            "不能当增加零件。"
        )
    file_part = added_part_row(sliced_nodes, after_number, old_nodes)
    if file_part is None or int(file_part.level) != expected_level:
        raise BusinessException(
            f"{EC_REVISE_FILE_CHAIN}：材料清单没有 {quoted(after_number)}，"
            f"或层级不是{quoted(change_order.part_level)}。"
        )
    if file_part.qty is None or file_part.qty <= 0:
        raise BusinessException(
            f"{EC_QTY_CHANGED}：增加零件 {quoted(after_number)} 用量必须大于 0，现在是 {file_part.qty}。"
        )
    if NOT_INSTALL_REMARK in (file_part.remark or ""):
        raise BusinessException(
            f"{EC_NOT_INSTALL_SIGNAL}：增加零件 {quoted(after_number)} 不要写「{NOT_INSTALL_REMARK}」。"
        )
    if expected_level != 2:
        return
    parent = _parent_node(sliced_nodes, file_part)
    if parent is None or int(parent.level) != 1:
        raise BusinessException(
            f"{EC_ADD_LEVEL1_NUMBER}：材料清单里 {quoted(after_number)} 的上级要是一级。"
        )
    parent_number = (parent.part_number or "").strip()
    pair = parent_level1_renumber(sliced_nodes, file_part, old_nodes)
    old_number = pair[0] if pair is not None else parent_number
    old_level1 = _find_old_level1(old_nodes, old_number)
    if old_level1 is None:
        return
    has_level2 = any(int(node.level) == 2 and node.parent_id == old_level1.id for node in old_nodes)
    if not has_level2:
        raise BusinessException(
            f"{EC_ADD_LEVEL1_LEAF}：{quoted(old_level1.part_number)} 下面没有二级，不能在它下面加零件。"
        )
    if pair is None:
        raise BusinessException(
            f"{EC_ADD_LEVEL1_NUMBER}：材料清单里 {quoted(after_number)} 的上级一级要写成新号。"
        )


def _find_old_level1(old_nodes: Sequence[BomNode], part_number: str) -> BomNode | None:
    return next(
        (
            node
            for node in old_nodes
            if int(node.level) == 1 and (node.part_number or "").strip() == part_number
        ),
        None,
    )


def _installed_level2_children(
    nodes: Sequence[BomParsedNode],
    parent: BomParsedNode,
) -> list[BomParsedNode]:
    """这一级下面实际装上的二级。用量 0、此件不装、空号不计入一套。"""
    parent_index = next((index for index, node in enumerate(nodes) if node is parent), None)
    if parent_index is None:
        return []
    children: list[BomParsedNode] = []
    for node in nodes:
        if int(node.level) != 2 or node.parent_index != parent_index:
            continue
        number = (node.part_number or "").strip()
        if not number or number == "/":
            continue
        if node.qty is None or node.qty <= 0:
            continue
        if NOT_INSTALL_REMARK in (node.remark or ""):
            continue
        children.append(node)
    return children


def _parent_node(
    nodes: Sequence[BomParsedNode],
    node: BomParsedNode,
) -> BomParsedNode | None:
    if node.parent_index is None:
        return None
    index = node.parent_index
    if index < 0 or index >= len(nodes):
        return None
    return nodes[index]


def _has_not_install_signal(nodes: Sequence[BomParsedNode], part_number: str) -> bool:
    """此件不装只认用量 0 且备注含这句话的那一行。同一号另外出现，不归这行管。"""
    for node in nodes:
        if int(node.level) == 0 or (node.part_number or "").strip() != part_number:
            continue
        if is_not_install_row(node.qty, node.remark, part_number=part_number):
            return True
    return False


def _require_old_part(change_order: ChangeOrderRowParsed, old_nodes: Sequence[BomNode]) -> BomNode:
    number = (change_order.before_part_number or "").strip()
    expected_level = PART_LEVEL_TO_BOM_LEVEL[change_order.part_level]
    match = next(
        (
            node
            for node in old_nodes
            if (node.part_number or "").strip() == number and int(node.level) == expected_level
        ),
        None,
    )
    if match is None:
        raise BusinessException(
            f"{EC_PART_NOT_ON_TREE}：{quoted(number)} 不在变更前总成上，"
            f"或不是{quoted(change_order.part_level)}。"
        )
    return match


def _old_chain_up(old_nodes: Sequence[BomNode], start: BomNode) -> list[BomNode]:
    by_id = {node.id: node for node in old_nodes}
    chain = [start]
    current = start
    while current.parent_id:
        parent = by_id.get(current.parent_id)
        if parent is None:
            break
        chain.append(parent)
        current = parent
    return chain


def _file_chain_up(nodes: list[BomParsedNode], start: BomParsedNode) -> list[BomParsedNode]:
    by_index = {index: node for index, node in enumerate(nodes)}
    chain = [start]
    current = start
    while current.parent_index is not None:
        parent = by_index.get(current.parent_index)
        if parent is None:
            break
        chain.append(parent)
        current = parent
    return chain


def _find_file_part(nodes: Sequence[BomParsedNode], part_number: str) -> BomParsedNode | None:
    target = (part_number or "").strip()
    if not target:
        return None
    for node in reversed(nodes):
        if (node.part_number or "").strip() == target:
            return node
    return None


def _old_descendants(old_nodes: Sequence[BomNode], parent_id: int) -> list[BomNode]:
    children_of: dict[int | None, list[BomNode]] = {}
    for node in old_nodes:
        children_of.setdefault(node.parent_id, []).append(node)
    found: list[BomNode] = []
    stack = list(children_of.get(parent_id, []))
    while stack:
        current = stack.pop()
        found.append(current)
        stack.extend(children_of.get(current.id, []))
    return found


def _needs_part_sketch(
    nodes: list[BomParsedNode],
    node: BomParsedNode,
    old_numbers: set[str] | None = None,
) -> bool:
    """一级叶子或二级需要单件图示。分总成、此件不装行、变更前总成上已有的原号，不要求新图。"""
    level = int(node.level)
    if level not in {1, 2}:
        return False
    if level == 1 and _file_has_children(nodes, node):
        return False
    if is_not_install_row(node.qty, node.remark, part_number=node.part_number):
        return False
    number = (node.part_number or "").strip()
    return number not in (old_numbers or set())


def _nodes_for_uniqueness(nodes: list[BomParsedNode]) -> list[BomParsedNode]:
    """此件不装那一行不参加一物一码。"""
    return [
        node
        for node in nodes
        if not is_not_install_row(node.qty, node.remark, part_number=node.part_number)
    ]


def _file_has_children(nodes: list[BomParsedNode], parent: BomParsedNode) -> bool:
    parent_index = next(
        (index for index, node in enumerate(nodes) if node is parent),
        None,
    )
    if parent_index is None:
        return False
    return any(node.parent_index == parent_index for node in nodes)


def _has_internal(value: str | None) -> bool:
    return bool((value or "").strip())
