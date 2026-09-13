"""覆盖上传时沿用子表分摊比例。"""

from __future__ import annotations

from decimal import Decimal

from app.common.money import Q2, quantize_money
from app.models.stamping.die import StampingDiePart
from app.parsers.stamping.die.parser import ParsedDiePart
from app.services.stamping.die.alloc_ratio_resolver import resolve_alloc_ratio

_SCRAP_BYPRODUCT_ALLOC_RATIO = Decimal("0.00")


def preserve_die_alloc(
    existing_parts: list[StampingDiePart],
) -> dict[str, dict[str, Decimal]]:
    """返回 part_number -> {process_seq: alloc_ratio}。新零件不在字典中。"""
    preserved: dict[str, dict[str, Decimal]] = {}
    for part in existing_parts:
        ratios: dict[str, Decimal] = {}
        for process in part.processes:
            seq = (process.process_seq or "").strip()
            if seq:
                ratios[seq] = quantize_money(process.alloc_ratio, Q2)
        preserved[(part.part_number or "").strip()] = ratios
    return preserved


def resolve_part_ratios(
    parsed: ParsedDiePart,
    preserved: dict[str, dict[str, Decimal]],
) -> list[Decimal]:
    if parsed.is_scrap_byproduct:
        return [quantize_money(_SCRAP_BYPRODUCT_ALLOC_RATIO, Q2) for _process in parsed.processes]
    by_seq = preserved.get(parsed.part_number.strip())
    default_ratio = resolve_alloc_ratio(parsed.die_method, parsed.production_mode)
    if by_seq is None:
        return [default_ratio for _process in parsed.processes]
    return [by_seq.get(process.process_seq.strip(), default_ratio) for process in parsed.processes]
