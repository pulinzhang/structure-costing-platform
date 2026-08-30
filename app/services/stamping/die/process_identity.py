"""布点零件对照冲压工艺：回填供应商与版本。"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from app.common.part_number import normalize_part_number_token

_MAX_ISSUE_LINES = 30


@dataclass(frozen=True, slots=True)
class ProcessPartIdentity:
    part_number: str
    stamping_supplier: str
    version: str


def map_die_parts_to_process(
    die_part_numbers: Sequence[str],
    process_rows: Sequence[ProcessPartIdentity],
) -> dict[str, ProcessPartIdentity]:
    """零件号 → 唯一工艺身份。对不上或一对多时抛 ValueError，文案可直接给用户。"""
    grouped: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in process_rows:
        number = normalize_part_number_token(row.part_number)
        supplier = (row.stamping_supplier or "").strip()
        version = (row.version or "").strip()
        if not number or not supplier or not version:
            continue
        grouped[number].add((supplier, version))

    missing: list[str] = []
    ambiguous: list[str] = []
    mapping: dict[str, ProcessPartIdentity] = {}
    seen: set[str] = set()
    for raw in die_part_numbers:
        number = normalize_part_number_token(raw)
        if not number or number in seen:
            continue
        seen.add(number)
        pairs = grouped.get(number)
        if not pairs:
            missing.append(number)
            continue
        if len(pairs) > 1:
            labels = "；".join(f"{supplier}/{version}" for supplier, version in sorted(pairs))
            ambiguous.append(f"{number}（{labels}）")
            continue
        supplier, version = next(iter(pairs))
        mapping[number] = ProcessPartIdentity(
            part_number=number,
            stamping_supplier=supplier,
            version=version,
        )

    if missing or ambiguous:
        raise ValueError(format_process_identity_issues(missing, ambiguous))
    return mapping


def format_process_identity_issues(missing: Sequence[str], ambiguous: Sequence[str]) -> str:
    lines = [
        "上传失败：布点零件须在同一基地+项目的冲压工艺中能唯一对应供应商与版本。"
        "导入已拒绝，未改已有布点。",
    ]
    if missing:
        lines.append(f"工艺中不存在（{len(missing)} 件）：")
        for number in missing[:_MAX_ISSUE_LINES]:
            lines.append(f"  {number}")
        extra = len(missing) - _MAX_ISSUE_LINES
        if extra > 0:
            lines.append(f"  …其余 {extra} 件")
    if ambiguous:
        lines.append(f"对应多个供应商或版本（{len(ambiguous)} 件）：")
        for item in ambiguous[:_MAX_ISSUE_LINES]:
            lines.append(f"  {item}")
        extra = len(ambiguous) - _MAX_ISSUE_LINES
        if extra > 0:
            lines.append(f"  …其余 {extra} 件")
    return "\n".join(lines)


def matches_die_identity(
    row_supplier: str | None,
    row_version: str | None,
    *,
    stamping_supplier: str | None,
    version: str | None,
) -> bool:
    """未选筛时全部匹配；选了则须与行上快照一致。"""
    return (not stamping_supplier or (row_supplier or "").strip() == stamping_supplier) and (
        not version or (row_version or "").strip() == version
    )
