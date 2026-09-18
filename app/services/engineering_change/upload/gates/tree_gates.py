"""变更单与材料清单、旧树对齐：缺层/错层/卸件双信号/内部号与总成图。"""

from __future__ import annotations

from collections.abc import Sequence

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    EC_ADD_ALREADY_ON_TREE,
    EC_ADD_VS_REVISE,
    EC_ASSEMBLY_SKETCH_REQUIRED,
    EC_CHANGE_ORDER_COLUMNS,
    EC_INTERNAL_REQUIRED,
    EC_NOT_INSTALL_CHILDREN,
    EC_NOT_INSTALL_SIGNAL,
    EC_PART_NOT_ON_TREE,
    EC_QTY_CHANGED,
    EC_REVISE_FILE_CHAIN,
    NOT_INSTALL_REMARK,
    PART_LEVEL_ASSEMBLY,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
    bump_letter_version,
    is_not_install_row,
    letter_version_base,
    letter_version_suffix,
)
from app.exceptions.base import BusinessException
from app.models.bom import BomNode
from app.parsers.bom.models import BomParsedNode
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed
from app.services.bom.internal_number_uniqueness import validate_internal_number_uniqueness

_LEVEL_BY_LABEL = {
    PART_LEVEL_ASSEMBLY: 0,
    PART_LEVEL_L1: 1,
    PART_LEVEL_L2: 2,
}


def validate_change_tree_gates(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    """一种改法：旧树有该件、清单写出该层、卸件双信号。完成停止不进。"""
    if change_order.change_type == CHANGE_TYPE_STOP:
        return
    file_l0 = [node for node in sliced_nodes if int(node.level) == 0]
    if file_l0 and is_not_install_row(file_l0[0].qty, file_l0[0].remark):
        raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
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
    """交货总成、分总成内部号；总成图；本张清单一物一码。"""
    validate_internal_number_uniqueness(sliced_nodes)
    l0_groups: dict[str, list[BomParsedNode]] = {}
    for node in sliced_nodes:
        if int(node.level) != 0:
            continue
        number = (node.part_number or "").strip()
        l0_groups.setdefault(number, []).append(node)
    for group in l0_groups.values():
        if not any(_has_internal(node.internal_number) for node in group):
            raise BusinessException(EC_INTERNAL_REQUIRED)
        if not any(node.sketch_bytes for node in group):
            raise BusinessException(EC_ASSEMBLY_SKETCH_REQUIRED)
    for node in sliced_nodes:
        if (
            int(node.level) == 1
            and _file_has_children(sliced_nodes, node)
            and not _has_internal(node.internal_number)
        ):
            raise BusinessException(EC_INTERNAL_REQUIRED)
    children_of: dict[int | None, list[BomNode]] = {}
    for old_node in old_nodes:
        children_of.setdefault(old_node.parent_id, []).append(old_node)
    for old_node in old_nodes:
        if int(old_node.level) == 0 and not _has_internal(old_node.internal_number):
            raise BusinessException(EC_INTERNAL_REQUIRED)
        if (
            int(old_node.level) == 1
            and children_of.get(old_node.id)
            and not _has_internal(old_node.internal_number)
        ):
            raise BusinessException(EC_INTERNAL_REQUIRED)


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
        raise BusinessException(EC_REVISE_FILE_CHAIN)
    by_id = {node.id: node for node in old_nodes}
    parent_id = old_part.parent_id
    while parent_id:
        parent = by_id.get(parent_id)
        if parent is None or int(parent.level) == 0:
            break
        parent_id = parent.parent_id
        old_number = (parent.part_number or "").strip()
        if not old_number or letter_version_suffix(old_number) is None:
            continue
        expected = bump_letter_version(old_number)
        file_parent = _find_file_part(sliced_nodes, expected)
        if file_parent is None or int(file_parent.level) != int(parent.level):
            raise BusinessException(EC_REVISE_FILE_CHAIN)


def _validate_not_install(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    old_part = _require_old_part(change_order, old_nodes)
    number = (change_order.before_part_number or "").strip()
    file_part = _find_file_part(sliced_nodes, number)
    if file_part is None or not is_not_install_row(file_part.qty, file_part.remark):
        raise BusinessException(EC_NOT_INSTALL_SIGNAL)
    descendants = _old_descendants(old_nodes, old_part.id)
    if not descendants:
        return
    for child in descendants:
        child_number = (child.part_number or "").strip()
        file_child = _find_file_part(sliced_nodes, child_number)
        if file_child is None or not is_not_install_row(file_child.qty, file_child.remark):
            raise BusinessException(EC_NOT_INSTALL_CHILDREN)


def _validate_add_part(
    change_order: ChangeOrderRowParsed,
    old_nodes: Sequence[BomNode],
    sliced_nodes: list[BomParsedNode],
) -> None:
    after_number = (change_order.after_part_number or "").strip()
    old_numbers = {(node.part_number or "").strip() for node in old_nodes}
    if after_number in old_numbers:
        raise BusinessException(EC_ADD_ALREADY_ON_TREE)
    after_base = letter_version_base(after_number)
    if after_base:
        for node in old_nodes:
            old_base = letter_version_base((node.part_number or "").strip())
            if old_base and old_base == after_base:
                raise BusinessException(EC_ADD_VS_REVISE)
    expected_level = _LEVEL_BY_LABEL[change_order.part_level]
    file_part = _find_file_part(sliced_nodes, after_number)
    if file_part is None or int(file_part.level) != expected_level:
        raise BusinessException(EC_REVISE_FILE_CHAIN)
    if file_part.qty is None or file_part.qty <= 0:
        raise BusinessException(EC_QTY_CHANGED)
    if NOT_INSTALL_REMARK in (file_part.remark or ""):
        raise BusinessException(EC_NOT_INSTALL_SIGNAL)


def _require_old_part(change_order: ChangeOrderRowParsed, old_nodes: Sequence[BomNode]) -> BomNode:
    number = (change_order.before_part_number or "").strip()
    expected_level = _LEVEL_BY_LABEL[change_order.part_level]
    match = next(
        (
            node
            for node in old_nodes
            if (node.part_number or "").strip() == number and int(node.level) == expected_level
        ),
        None,
    )
    if match is None:
        raise BusinessException(EC_PART_NOT_ON_TREE)
    return match


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
