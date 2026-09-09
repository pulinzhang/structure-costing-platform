"""BOM 一物一码：有内部号的物料，零件号与内部号必须一一对应。"""

from __future__ import annotations

from collections import defaultdict

from app.exceptions.base import BusinessException
from app.parsers.bom.models import BomParsedNode


def _text(value: str | None) -> str:
    return (value or "").strip()


def _part_key(value: str | None) -> str:
    return _text(value).upper()


def _row_label(node: BomParsedNode) -> str:
    if node.source_row is not None:
        return f"第 {node.source_row} 行"
    return f"序号 {node.sort_no}"


def _node_line(node: BomParsedNode) -> str:
    part_number = _text(node.part_number) or "-"
    internal_number = _text(node.internal_number) or "-"
    part_name = _text(node.part_name)
    name_suffix = f" {part_name}" if part_name else ""
    return (
        f"- Excel {_row_label(node)}：L{int(node.level)} "
        f"零件号 {part_number}{name_suffix}，内部号 {internal_number}"
    )


def _conflict_block(title: str, indices: list[int], nodes: list[BomParsedNode]) -> str:
    lines = [title]
    ordered = sorted(
        indices,
        key=lambda i: (
            nodes[i].source_row if nodes[i].source_row is not None else 10**9,
            nodes[i].sort_no,
        ),
    )
    for index in ordered:
        lines.append(_node_line(nodes[index]))
    return "\n".join(lines)


def validate_internal_number_uniqueness(nodes: list[BomParsedNode]) -> None:
    """
    有内部号才进 ERP：同一零件号只能有一个内部号，同一内部号只能对应一个零件号。

    内部号为空的行不参与（标准件/耗材等可不进 ERP）。比较时去空白并忽略大小写。
    """
    by_part: dict[str, list[int]] = defaultdict(list)
    by_internal: dict[str, list[int]] = defaultdict(list)
    for index, node in enumerate(nodes):
        internal_key = _part_key(node.internal_number)
        if not internal_key:
            continue
        part_key = _part_key(node.part_number)
        if not part_key:
            continue
        by_part[part_key].append(index)
        by_internal[internal_key].append(index)

    conflicts: list[str] = []
    for part_key, indices in sorted(by_part.items()):
        internals = {_part_key(nodes[i].internal_number) for i in indices}
        if len(internals) <= 1:
            continue
        display_part = _text(nodes[indices[0]].part_number) or part_key
        conflicts.append(_conflict_block(f"零件号 {display_part} 对应多个内部号：", indices, nodes))

    for internal_key, indices in sorted(by_internal.items()):
        parts = {_part_key(nodes[i].part_number) for i in indices}
        if len(parts) <= 1:
            continue
        display_internal = _text(nodes[indices[0]].internal_number) or internal_key
        conflicts.append(
            _conflict_block(
                f"内部号 {display_internal} 对应多个零件号：",
                indices,
                nodes,
            )
        )

    if not conflicts:
        return

    detail = "\n".join(conflicts)
    raise BusinessException(
        "进 ERP 的物料必须一物一码"
        "（同一零件号只能对应一个内部号，同一内部号只能对应一个零件号），"
        "请改正确后再上传：\n"
        f"{detail}"
    )
