"""共模共用序：无本行重量时继承上一件已解析重量。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.common.scrap_byproduct import layout_is_scrap_byproduct_part
from app.models.stamping.die import StampingDiePart, StampingDieProcess
from app.services.stamping.die_fee.rules.fee_math import ZERO

WEIGHT_SOURCE_SELF = "self"
WEIGHT_SOURCE_INHERITED = "inherited"

_SHARED_MARKERS = ("合并", "双槽", "一出二", "共用")


@dataclass(frozen=True, slots=True)
class ResolvedDieWeight:
    weight_t: Decimal
    source: str
    inherited_from_part_number: str | None = None
    inherited_from_process_seq: str | None = None


@dataclass(slots=True)
class PreviousWeightIndex:
    by_seq: dict[str, Decimal] = field(default_factory=dict)
    by_order: dict[int, Decimal] = field(default_factory=dict)
    part_number: str | None = None
    seq_by_order: dict[int, str] = field(default_factory=dict)


def has_shared_marker(text: str | None) -> bool:
    if not text:
        return False
    value = str(text).strip()
    return any(marker in value for marker in _SHARED_MARKERS)


def own_die_weight_t(process: StampingDieProcess) -> Decimal | None:
    weight = process.estimated_weight_t
    if weight is None or weight <= ZERO:
        return None
    return weight


def has_real_die_dimensions(process: StampingDieProcess) -> bool:
    """上一件该序须有真实长、宽、高，空外形行不得把解析重量再传给下一件。"""
    length = process.die_length
    width = process.die_width
    height = process.die_height
    if length is None or width is None or height is None:
        return False
    return length > ZERO and width > ZERO and height > ZERO


def can_inherit_previous_weight(part: StampingDiePart, process: StampingDieProcess) -> bool:
    """零件模具方式/生产方式，或本序/同件工序代码含共模标记。废料副产品不继承。"""
    if layout_is_scrap_byproduct_part(part):
        return False
    if has_shared_marker(part.die_method) or has_shared_marker(part.production_mode):
        return True
    if has_shared_marker(process.process_code):
        return True
    return any(has_shared_marker(sibling.process_code) for sibling in part.processes or [])


def match_previous_weight(
    process: StampingDieProcess,
    previous: PreviousWeightIndex,
) -> tuple[Decimal, str] | None:
    seq = (process.process_seq or "").strip()
    if seq and seq in previous.by_seq:
        return previous.by_seq[seq], seq
    order = process.process_order
    if order is not None and order in previous.by_order:
        from_seq = previous.seq_by_order.get(order) or str(order)
        return previous.by_order[order], from_seq
    return None


def resolve_process_weight(
    part: StampingDiePart,
    process: StampingDieProcess,
    previous: PreviousWeightIndex,
) -> ResolvedDieWeight | None:
    own = own_die_weight_t(process)
    if own is not None:
        return ResolvedDieWeight(weight_t=own, source=WEIGHT_SOURCE_SELF)
    if not can_inherit_previous_weight(part, process):
        return None
    matched = match_previous_weight(process, previous)
    if matched is None:
        return None
    weight, from_seq = matched
    return ResolvedDieWeight(
        weight_t=weight,
        source=WEIGHT_SOURCE_INHERITED,
        inherited_from_part_number=previous.part_number,
        inherited_from_process_seq=from_seq,
    )


def index_resolved_weights(
    part: StampingDiePart,
    resolved: dict[str, ResolvedDieWeight],
) -> PreviousWeightIndex:
    index = PreviousWeightIndex(part_number=part.part_number)
    for process in part.processes or []:
        if not has_real_die_dimensions(process):
            continue
        seq = (process.process_seq or "").strip()
        item = resolved.get(seq) if seq else None
        if item is None:
            continue
        if seq:
            index.by_seq[seq] = item.weight_t
        order = process.process_order
        if order is not None:
            index.by_order[order] = item.weight_t
            index.seq_by_order[order] = seq or str(order)
    return index


def resolve_part_weights(
    part: StampingDiePart,
    previous: PreviousWeightIndex,
) -> dict[str, ResolvedDieWeight]:
    resolved: dict[str, ResolvedDieWeight] = {}
    for process in part.processes or []:
        seq = (process.process_seq or "").strip()
        if not seq:
            continue
        item = resolve_process_weight(part, process, previous)
        if item is not None:
            resolved[seq] = item
    return resolved
