"""变更单与材料清单、旧树对齐：缺层/错层/卸件双信号/内部号、总成图与一级单件图示。"""

from __future__ import annotations

from collections.abc import Sequence

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    EC_ADD_ALREADY_ON_TREE,
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
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed
from app.services.bom.internal_number_uniqueness import validate_internal_number_uniqueness


def validate_change_tree_gates(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    """一种改法：旧树有该件、清单写出该层、卸件双信号。完成停止不进。"""
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


def validate_identity_gates(
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    """交货总成、分总成内部号；总成图（合并总成一张即可）；一二级单件图示；本张清单一物一码。"""
    validate_internal_number_uniqueness(sliced_nodes)
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
    for node in sliced_nodes:
        if not _needs_part_sketch(sliced_nodes, node):
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
    file_part = _find_file_part(sliced_nodes, number)
    if file_part is None:
        raise BusinessException(
            f"{EC_NOT_INSTALL_SIGNAL}：材料清单没有 {quoted(number)}。"
            f"此件不装必须用量 0 且备注含「{NOT_INSTALL_REMARK}」。"
        )
    if not is_not_install_row(file_part.qty, file_part.remark, part_number=number):
        raise BusinessException(
            f"{EC_NOT_INSTALL_SIGNAL}：材料清单里 {quoted(number)} "
            f"必须用量 0 且备注含「{NOT_INSTALL_REMARK}」。"
        )
    descendants = _old_descendants(old_nodes, old_part.id)
    if not descendants:
        return
    for child in descendants:
        child_number = (child.part_number or "").strip()
        file_child = _find_file_part(sliced_nodes, child_number)
        if file_child is None:
            raise BusinessException(
                f"{EC_NOT_INSTALL_CHILDREN}：{quoted(child_number)} 是不装件的下级，"
                f"材料清单也要用量 0 且备注含「{NOT_INSTALL_REMARK}」。"
            )
        if not is_not_install_row(file_child.qty, file_child.remark, part_number=child_number):
            raise BusinessException(
                f"{EC_NOT_INSTALL_CHILDREN}：{quoted(child_number)} 是不装件的下级，"
                f"材料清单也要用量 0 且备注含「{NOT_INSTALL_REMARK}」。"
            )


def _validate_add_part(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    after_number = (change_order.after_part_number or "").strip()
    old_numbers = {(node.part_number or "").strip() for node in old_nodes}
    if after_number in old_numbers:
        raise BusinessException(
            f"{EC_ADD_ALREADY_ON_TREE}：{quoted(after_number)} 已在变更前总成上，不能当增加零件。"
        )
    expected_level = PART_LEVEL_TO_BOM_LEVEL[change_order.part_level]
    file_part = _find_file_part(sliced_nodes, after_number)
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


def _find_file_part(nodes: list[BomParsedNode], part_number: str) -> BomParsedNode | None:
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


def _needs_part_sketch(nodes: list[BomParsedNode], node: BomParsedNode) -> bool:
    """一级叶子或二级需要单件图示；分总成图归下级；此件不装不要求。"""
    level = int(node.level)
    if level not in {1, 2}:
        return False
    if level == 1 and _file_has_children(nodes, node):
        return False
    return not is_not_install_row(node.qty, node.remark, part_number=node.part_number)


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
