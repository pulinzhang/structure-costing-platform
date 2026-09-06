"""有长宽高但无模具号：只提示，不拦截。共模共用序不提示。"""

from __future__ import annotations

from app.models.stamping.die import StampingDiePart, StampingDieProcess
from app.services.stamping.die_fee.calc.weight_resolver import (
    has_real_die_dimensions,
    has_shared_marker,
)

_HINT_LIMIT = 30


def process_needs_die_number_hint(process: StampingDieProcess) -> bool:
    if has_shared_marker(process.process_code):
        return False
    if not has_real_die_dimensions(process):
        return False
    return not (process.die_number or "").strip()


def hint_line(
    part_number: str,
    process_seq: str | None,
) -> str:
    seq = (process_seq or "").strip() or "-"
    return f"零件 {part_number} 工序 {seq} 已有模具长/宽/高，但没有模具编号"


def collect_missing_die_number_hints(part: StampingDiePart) -> list[str]:
    return [
        hint_line(part.part_number, process.process_seq)
        for process in part.processes or []
        if process_needs_die_number_hint(process)
    ]


def format_missing_die_number_section(hints: list[str], *, limit: int = _HINT_LIMIT) -> str:
    if not hints:
        return ""
    lines = [f"有尺寸但无模具编号（仅提示，未拦截）{len(hints)} 处："]
    for item in hints[:limit]:
        lines.append(f"  {item}")
    extra = len(hints) - limit
    if extra > 0:
        lines.append(f"  另有 {extra} 处未列出")
    return "\n".join(lines)
