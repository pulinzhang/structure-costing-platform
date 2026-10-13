"""旧号 → 新号（此件不装为 None）。中间分总成只认材料清单已写出的号。"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_ADD_SUBASSEMBLY,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    PART_LEVEL_ASSEMBLY,
    has_not_install_marks,
)
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import BomParsedNode
from app.services.bom.bom.change_tree_plant.types import BomChangePlantSpec

_VERSIONED_PART = re.compile(r"^(?P<body>\d+)(?P<version>[A-Z]{2})(?P<tail>-\d+)?$")


def build_number_map(
    spec: BomChangePlantSpec,
    old_nodes: list[BomNode],
    parsed_nodes: list[BomParsedNode],
    extra_specs: Sequence[BomChangePlantSpec] = (),
) -> dict[str, str | None]:
    specs = (spec, *extra_specs)
    subassembly_numbers = subassembly_part_numbers(
        (item.change_type, item.after_part_number) for item in specs
    )
    mapping: dict[str, str | None] = {
        spec.before_assembly_part_number: spec.after_assembly_part_number
    }
    for item in specs:
        _apply_spec(mapping, item, old_nodes, parsed_nodes, subassembly_numbers)
    return mapping


def _apply_spec(
    mapping: dict[str, str | None],
    spec: BomChangePlantSpec,
    old_nodes: list[BomNode],
    parsed_nodes: list[BomParsedNode],
    subassembly_numbers: set[str],
) -> None:
    if spec.change_type == CHANGE_TYPE_REVISE:
        if spec.part_level != PART_LEVEL_ASSEMBLY and spec.before_part_number:
            mapping[spec.before_part_number] = spec.after_part_number
            _map_revise_ancestor_chain(
                mapping,
                old_nodes,
                parsed_nodes,
                spec.before_part_number,
                spec.after_part_number,
            )
    elif spec.change_type == CHANGE_TYPE_ADD_PART and spec.after_part_number:
        pair = level1_renumber_for_added_part(
            old_nodes,
            parsed_nodes,
            spec.after_part_number,
            subassembly_numbers=subassembly_numbers,
        )
        if pair is not None:
            old_number, file_number = pair
            mapping.setdefault(old_number, file_number)
    elif spec.change_type == CHANGE_TYPE_NOT_INSTALL and spec.before_part_number:
        mapping[spec.before_part_number] = None
        if spec.after_assembly_part_number:
            mapping[spec.before_assembly_part_number] = spec.after_assembly_part_number


def part_installed_at_level(
    nodes: Sequence[BomNode],
    part_number: str,
    bom_level: int,
) -> bool:
    """本行层级上是否已有这个零件号。同一号装在别的层级，归那一行。"""
    number = (part_number or "").strip()
    if not number:
        return False
    for node in nodes:
        if (node.part_number or "").strip() == number and int(node.level) == bom_level:
            return True
    return False


def subassembly_part_numbers(specs: Iterable[tuple[str, str | None]]) -> set[str]:
    """增加分总成写出的变更后零件号。"""
    return {
        number
        for change_type, after_part_number in specs
        if change_type == CHANGE_TYPE_ADD_SUBASSEMBLY
        and (number := (after_part_number or "").strip())
    }


def added_part_rows(
    parsed_nodes: Sequence[BomParsedNode],
    old_nodes: Sequence[BomNode],
    subassembly_numbers: set[str] | None = None,
) -> dict[str, BomParsedNode]:
    """每个零件号只留增加零件那一行。"""
    rows: dict[str, BomParsedNode] = {}
    for node in parsed_nodes:
        number = (node.part_number or "").strip()
        if int(node.level) == 0 or not number or number in rows:
            continue
        row = added_part_row(parsed_nodes, number, old_nodes, subassembly_numbers)
        if row is not None:
            rows[number] = row
    return rows


def added_part_row(
    parsed_nodes: Sequence[BomParsedNode],
    part_number: str,
    old_nodes: Sequence[BomNode],
    subassembly_numbers: set[str] | None = None,
) -> BomParsedNode | None:
    """增加零件这一行。此件不装、新分总成下面的行不算。上级对得上旧一级换号的优先。"""
    return _chosen_added_part(parsed_nodes, part_number, old_nodes, subassembly_numbers)


def level1_renumber_for_added_part(
    old_nodes: Sequence[BomNode],
    parsed_nodes: Sequence[BomParsedNode],
    after_part_number: str,
    subassembly_numbers: set[str] | None = None,
) -> tuple[str, str] | None:
    """增加二级：材料清单里增加零件那一行的上级一级新号，对应旧树上的原号。

    新号以材料清单为准，不把 AA 加成 AB。对不上唯一的旧一级，返回 None。
    """
    file_part = added_part_row(
        parsed_nodes,
        after_part_number,
        old_nodes,
        subassembly_numbers,
    )
    if file_part is None:
        return None
    return parent_level1_renumber(parsed_nodes, file_part, old_nodes)


def _chosen_added_part(
    parsed_nodes: Sequence[BomParsedNode],
    part_number: str,
    old_nodes: Sequence[BomNode],
    subassembly_numbers: set[str] | None,
) -> BomParsedNode | None:
    target = (part_number or "").strip()
    blocked = subassembly_numbers or set()
    version_hit: BomParsedNode | None = None
    version_pair: tuple[str, str] | None = None
    other: BomParsedNode | None = None
    for node in parsed_nodes:
        if int(node.level) == 0 or (node.part_number or "").strip() != target:
            continue
        if has_not_install_marks(node.qty, node.remark):
            continue
        if hangs_under_level1(parsed_nodes, node, blocked):
            continue
        pair = parent_level1_renumber(parsed_nodes, node, old_nodes)
        if pair is None:
            other = node
            continue
        if version_hit is not None and pair != version_pair:
            return None
        version_hit = node
        version_pair = pair
    if version_hit is not None:
        return version_hit
    return other


def parent_level1_renumber(
    parsed_nodes: Sequence[BomParsedNode],
    file_part: BomParsedNode,
    old_nodes: Sequence[BomNode],
) -> tuple[str, str] | None:
    """二级行的上级一级是旧一级换了版本时，返回 (旧号, 材料清单上的新号)。"""
    if int(file_part.level) != 2 or file_part.parent_index is None:
        return None
    if file_part.parent_index < 0 or file_part.parent_index >= len(parsed_nodes):
        return None
    file_parent = parsed_nodes[file_part.parent_index]
    if int(file_parent.level) != 1:
        return None
    file_number = (file_parent.part_number or "").strip()
    file_key = _version_key(file_number)
    if file_key is None:
        return None
    file_body, file_version = file_key
    matches = [
        (node.part_number or "").strip()
        for node in old_nodes
        if int(node.level) == 1
        and _is_same_part_new_version(node.part_number, file_body, file_version)
    ]
    if len(matches) != 1:
        return None
    return matches[0], file_number


def hangs_under_level1(
    parsed_nodes: Sequence[BomParsedNode],
    node: BomParsedNode,
    part_numbers: set[str],
) -> bool:
    current = node
    while current.parent_index is not None:
        parent = parsed_nodes[current.parent_index]
        if int(parent.level) == 1 and (parent.part_number or "").strip() in part_numbers:
            return True
        current = parent
    return False


def _is_same_part_new_version(
    old_part_number: str | None,
    file_body: str,
    file_version: str,
) -> bool:
    old_key = _version_key(old_part_number or "")
    if old_key is None:
        return False
    old_body, old_version = old_key
    return old_body == file_body and old_version != file_version


def _version_key(part_number: str) -> tuple[str, str] | None:
    match = _VERSIONED_PART.fullmatch(part_number.strip())
    if match is None:
        return None
    return match.group("body") + (match.group("tail") or ""), match.group("version")


def _map_revise_ancestor_chain(
    mapping: dict[str, str | None],
    old_nodes: list[BomNode],
    parsed_nodes: list[BomParsedNode],
    before_part_number: str,
    after_part_number: str | None,
) -> None:
    """改图中间分总成：旧树位置对材料清单写出的号，禁止自己进一位。"""
    after_number = (after_part_number or "").strip()
    if not after_number:
        return
    old_part = next(
        (
            node
            for node in old_nodes
            if (node.part_number or "").strip() == before_part_number.strip()
        ),
        None,
    )
    file_part = next(
        (
            node
            for node in reversed(parsed_nodes)
            if (node.part_number or "").strip() == after_number
        ),
        None,
    )
    if old_part is None or file_part is None:
        return
    old_by_id = {node.id: node for node in old_nodes}
    file_by_index = {index: node for index, node in enumerate(parsed_nodes)}
    old_current = old_part
    file_current = file_part
    while old_current.parent_id and file_current.parent_index is not None:
        old_parent = old_by_id.get(old_current.parent_id)
        file_parent = file_by_index.get(file_current.parent_index)
        if old_parent is None or file_parent is None:
            break
        if int(old_parent.level) == 0:
            break
        old_number = (old_parent.part_number or "").strip()
        file_number = (file_parent.part_number or "").strip()
        if old_number and file_number and old_number not in mapping:
            mapping[old_number] = file_number
        old_current = old_parent
        file_current = file_parent
