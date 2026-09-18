"""旧号 → 新号（此件不装为 None）。中间分总成只认材料清单已写出的号。"""

from __future__ import annotations

from collections.abc import Sequence

from app.common.engineering_change_gates import (
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    PART_LEVEL_ASSEMBLY,
)
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import BomParsedNode
from app.services.bom.change_tree_plant.types import BomChangePlantSpec


def build_number_map(
    spec: BomChangePlantSpec,
    old_nodes: list[BomNode],
    parsed_nodes: list[BomParsedNode],
    extra_specs: Sequence[BomChangePlantSpec] = (),
) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {
        spec.before_assembly_part_number: spec.after_assembly_part_number
    }
    for item in (spec, *extra_specs):
        _apply_spec(mapping, item, old_nodes, parsed_nodes)
    return mapping


def _apply_spec(
    mapping: dict[str, str | None],
    spec: BomChangePlantSpec,
    old_nodes: list[BomNode],
    parsed_nodes: list[BomParsedNode],
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
    elif spec.change_type == CHANGE_TYPE_NOT_INSTALL and spec.before_part_number:
        mapping[spec.before_part_number] = None
        if spec.after_assembly_part_number:
            mapping[spec.before_assembly_part_number] = spec.after_assembly_part_number


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
