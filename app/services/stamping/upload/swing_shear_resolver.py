"""上传时汇总含摆剪的零件号（含合并右件继承上一件）。"""

from app.common.swing_shear import is_swing_shear_label
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.services.stamping.upload.cost_ratio_resolver import is_mate_process_code


def collect_swing_shear_part_numbers(
    parts: list[Part],
    processes: list[Process],
) -> set[str]:
    """
    本件写了摆剪，或 Excel 上一件是摆剪且本件第一序为合并/双槽/共用。

    右件第一序常只写「合并」，不再重复「摆剪」；与上一件共模同冲，主表也记摆剪。
    """
    numbers: set[str] = set()
    processes_by_part: dict[str, list[Process]] = {}
    for process in processes:
        part_number = (process.part_number or "").strip()
        if not part_number:
            continue
        processes_by_part.setdefault(part_number, []).append(process)
        if is_swing_shear_label(process.process_code, process.process_seq):
            numbers.add(part_number)

    ordered: list[str] = []
    for part in parts:
        part_number = (part.part_number or "").strip()
        if not part_number:
            continue
        ordered.append(part_number)
        if part.has_swing_shear:
            numbers.add(part_number)

    previous_number: str | None = None
    for part_number in ordered:
        siblings = processes_by_part.get(part_number, [])
        first_code = siblings[0].process_code if siblings else None
        if previous_number and previous_number in numbers and is_mate_process_code(first_code):
            numbers.add(part_number)
        previous_number = part_number
    return numbers
