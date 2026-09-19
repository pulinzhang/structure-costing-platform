"""抄旧树字段：材料属性、内部号、增加件 excel_row。禁止写入工程变更行号。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar

from app.common.engineering_change_gates import EC_QTY_CHANGED, is_not_install_row
from app.exceptions.base import BusinessException
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import BomParsedNode

_Value = TypeVar("_Value")


@dataclass(slots=True)
class CopiedChildFields:
    qty: Decimal | None
    part_name: str | None
    material: str | None
    weld_info: str | None
    remark: str | None
    thickness_mm: Decimal | None
    thickness_text: str | None
    material_mill: str | None
    part_weight: Decimal | None
    gauge_developed: str | None
    qty_text: str | None


def _file_or_old(file_value: _Value | None, old_value: _Value | None) -> _Value | None:
    return file_value if file_value is not None else old_value


def internal_from_file(file_row: BomParsedNode | None, old_value: str | None) -> str | None:
    if file_row is None:
        return old_value
    text = (file_row.internal_number or "").strip()
    if text:
        return text
    return old_value


def copied_child_fields(
    *,
    old_node: BomNode,
    file_row: BomParsedNode | None,
    has_add_part: bool,
    number_map: dict[str, str | None],
) -> CopiedChildFields | None:
    """工程变更变化行覆盖属性；此件不装返回 None。"""
    if file_row is not None and is_not_install_row(file_row.qty, file_row.remark):
        return None
    if (
        file_row is not None
        and file_row.qty is not None
        and old_node.qty is not None
        and Decimal(str(file_row.qty)) != Decimal(str(old_node.qty))
        and not has_add_part
    ):
        raise BusinessException(EC_QTY_CHANGED)
    qty = old_node.qty
    if file_row is not None and has_add_part and old_node.part_number not in number_map:
        qty = file_row.qty
    return CopiedChildFields(
        qty=qty,
        part_name=(file_row.part_name or old_node.part_name)
        if file_row is not None
        else old_node.part_name,
        material=_file_or_old(file_row.material if file_row else None, old_node.material),
        weld_info=_file_or_old(file_row.weld_info if file_row else None, old_node.weld_info),
        remark=_file_or_old(file_row.remark if file_row else None, old_node.remark),
        thickness_mm=_file_or_old(
            file_row.thickness_mm if file_row else None, old_node.thickness_mm
        ),
        thickness_text=_file_or_old(
            file_row.thickness_text if file_row else None, old_node.thickness_text
        ),
        material_mill=_file_or_old(
            file_row.material_mill if file_row else None, old_node.material_mill
        ),
        part_weight=_file_or_old(file_row.part_weight if file_row else None, old_node.part_weight),
        gauge_developed=_file_or_old(
            file_row.gauge_developed if file_row else None, old_node.gauge_developed
        ),
        qty_text=_file_or_old(file_row.qty_text if file_row else None, old_node.qty_text),
    )


def excel_row_for_added_part(
    *,
    add_row: BomParsedNode,
    parsed_nodes: list[BomParsedNode],
    excel_row_by_part: dict[str, int | None],
) -> int | None:
    """增加件没有 SOP 行号：抄工程变更里前一个已种兄弟的旧树 excel_row。"""
    siblings = [
        node
        for node in parsed_nodes
        if node.parent_index == add_row.parent_index and node.level == add_row.level
    ]
    siblings.sort(key=lambda node: (node.source_row or 0, node.sort_no, node.part_number))
    add_index = next(
        (index for index, node in enumerate(siblings) if node.part_number == add_row.part_number),
        None,
    )
    if add_index is None:
        return None
    for node in reversed(siblings[:add_index]):
        row = excel_row_by_part.get(node.part_number)
        if row is not None:
            return row
    for node in siblings[add_index + 1 :]:
        row = excel_row_by_part.get(node.part_number)
        if row is not None:
            return max(row - 1, 0)
    return None
