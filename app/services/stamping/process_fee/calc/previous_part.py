"""共用件按零件序号找上一件（禁止用 id-1）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.common.period import period
from app.models.stamping import StampingPart

_OPEN_END = period(9999, 12)


def _period_end(part: StampingPart) -> tuple[int, int]:
    if part.expiry_year is None or part.expiry_month is None:
        return _OPEN_END
    return period(int(part.expiry_year), int(part.expiry_month))


def parts_periods_overlap(left: StampingPart, right: StampingPart) -> bool:
    """两件有效期闭区间有交集（同年账里新旧号同序号时用来认一代）。"""
    left_start = period(int(left.effective_year), int(left.effective_month))
    right_start = period(int(right.effective_year), int(right.effective_month))
    return left_start <= _period_end(right) and right_start <= _period_end(left)


def _scope_key(part: StampingPart) -> tuple[str, str, str]:
    return (
        (part.location or "").strip(),
        (part.vehicle_model or "").strip(),
        (part.stamping_supplier or "").strip(),
    )


@dataclass(slots=True)
class PreviousPartIndex:
    """计算清单里按 (基地, 项目, 冲压厂, seq_no) 找共用上一件。"""

    _by_scope_seq: dict[tuple[str, str, str, int], list[StampingPart]] = field(default_factory=dict)

    @classmethod
    def from_parts(cls, parts: Sequence[StampingPart]) -> PreviousPartIndex:
        grouped: dict[tuple[str, str, str, int], list[StampingPart]] = {}
        for part in parts:
            seq_no = part.seq_no
            if seq_no is None:
                continue
            key = (*_scope_key(part), int(seq_no))
            grouped.setdefault(key, []).append(part)
        return cls(_by_scope_seq=grouped)

    def get_previous(self, part: StampingPart) -> StampingPart | None:
        seq_no = part.seq_no
        if seq_no is None or seq_no <= 1:
            return None
        key = (*_scope_key(part), int(seq_no) - 1)
        matched = [
            candidate
            for candidate in self._by_scope_seq.get(key, [])
            if parts_periods_overlap(candidate, part)
        ]
        if not matched:
            return None
        if len(matched) == 1:
            return matched[0]
        return max(
            matched,
            key=lambda row: (
                int(row.effective_year),
                int(row.effective_month),
                row.part_number or "",
            ),
        )
