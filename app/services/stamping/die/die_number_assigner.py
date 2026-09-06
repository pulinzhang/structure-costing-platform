"""布点上传：有外形且缺号时按 DP-40-{项目}-流水补号。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException
from app.parsers.stamping_die.parser import ParsedDiePart, ParsedDieProcess

_PREFIX = "DP"
_CATEGORY = "40"
_SERIAL_MAX = 999
_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class AssignedDieNumbers:
    by_key: dict[tuple[str, str], str | None]
    assigned_count: int


def has_any_positive_dimension(
    die_length: Decimal | None,
    die_width: Decimal | None,
    die_height: Decimal | None,
) -> bool:
    return any(value is not None and value > _ZERO for value in (die_length, die_width, die_height))


def occupied_serials(vehicle_model: str, numbers: list[str | None]) -> set[int]:
    model = normalize_vehicle_model(vehicle_model) or ""
    if not model:
        return set()
    pattern = re.compile(
        rf"^{re.escape(_PREFIX)}-{re.escape(_CATEGORY)}-{re.escape(model)}-(\d{{3}})$"
    )
    found: set[int] = set()
    for raw in numbers:
        text = (raw or "").strip()
        match = pattern.fullmatch(text)
        if match:
            found.add(int(match.group(1)))
    return found


def format_die_number(vehicle_model: str, serial: int) -> str:
    model = normalize_vehicle_model(vehicle_model) or ""
    return f"{_PREFIX}-{_CATEGORY}-{model}-{serial:03d}"


def _needs_assignment(process: ParsedDieProcess) -> bool:
    if (process.die_number or "").strip():
        return False
    return has_any_positive_dimension(process.die_length, process.die_width, process.die_height)


def assign_die_numbers(
    *,
    vehicle_model: str,
    parts: list[ParsedDiePart],
    existing_numbers: list[str],
) -> AssignedDieNumbers:
    model = normalize_vehicle_model(vehicle_model) or ""
    if not model:
        raise BusinessException("请填写项目")

    file_numbers = [process.die_number for part in parts for process in part.processes]
    occupied = occupied_serials(model, [*existing_numbers, *file_numbers])
    next_serial = (max(occupied) if occupied else 0) + 1

    rows: list[tuple[int, str, ParsedDieProcess]] = []
    for part in parts:
        for process in part.processes:
            rows.append((process.excel_row or 0, part.part_number, process))
    rows.sort(key=lambda item: (item[0], item[1], item[2].process_seq))

    by_key: dict[tuple[str, str], str | None] = {}
    assigned_count = 0
    for _excel_row, part_number, process in rows:
        key = (part_number.strip(), process.process_seq.strip())
        existing = (process.die_number or "").strip() or None
        if existing:
            by_key[key] = existing
            continue
        if not _needs_assignment(process):
            by_key[key] = None
            continue
        if next_serial > _SERIAL_MAX:
            raise BusinessException(
                f"项目 {model} 本规则模具编号已满（{_PREFIX}-{_CATEGORY}-{model}-999），"
                "请在 Excel 自行编号或清理占用号"
            )
        by_key[key] = format_die_number(model, next_serial)
        next_serial += 1
        assigned_count += 1
    return AssignedDieNumbers(by_key=by_key, assigned_count=assigned_count)
