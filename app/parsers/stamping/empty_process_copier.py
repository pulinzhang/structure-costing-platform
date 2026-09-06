"""共模右件工序格为空时，按 Excel 行序抄上一件工序。"""

from __future__ import annotations

from dataclasses import replace

from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process


def copy_empty_processes_from_previous(
    parts: list[Part],
    processes: list[Process],
) -> list[str]:
    """
    本件没有任何有效工序（无工序代码、吨位、模具编号）时，
    把上一件已解析工序抄过来落库。废料副产品不抄。

    原地改 ``processes``。返回被补齐的零件号（Excel 出现顺序）。
    """
    by_number: dict[str, list[Process]] = {}
    for process in processes:
        number = (process.part_number or "").strip()
        if not number:
            continue
        by_number.setdefault(number, []).append(process)

    filled: list[str] = []
    previous: list[Process] = []
    copies: list[Process] = []
    drop: set[int] = set()

    for part in parts:
        part_number = (part.part_number or "").strip()
        if not part_number:
            continue
        current = by_number.get(part_number, [])
        if part.is_scrap_byproduct:
            if _has_usable_process(current):
                previous = current
            continue
        if _has_usable_process(current):
            previous = current
            continue
        if not previous:
            continue
        for process in current:
            drop.add(id(process))
        excel_row = part.excel_row
        for source in previous:
            copies.append(
                replace(
                    source,
                    part_number=part_number,
                    excel_row=excel_row,
                )
            )
        filled.append(part_number)

    if drop:
        processes[:] = [process for process in processes if id(process) not in drop]
    processes.extend(copies)
    return filled


def empty_process_warning_text(part_number: str) -> str:
    return f"零件 {part_number} 没有任何工序"


def _has_usable_process(processes: list[Process]) -> bool:
    return any(not _is_blank_process(process) for process in processes)


def _is_blank_process(process: Process) -> bool:
    code = str(process.process_code or "").strip()
    die_number = (process.die_number or "").strip()
    return not code and process.tonnage is None and not die_number
