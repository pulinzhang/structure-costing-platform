"""模具布点数据行：零件行、工序行与数值转换。"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from openpyxl.worksheet.worksheet import Worksheet

from app.common.money import Q2, Q4, parse_decimal, quantize_money
from app.common.scrap_byproduct import layout_is_scrap_byproduct

from .columns import cell
from .types import DieColumnMap, ParsedDiePart, ParsedDieProcess


def parse_unit_interval(value: object) -> Decimal | None:
    """材料利用率：入库 0～1。Excel 写成 65 / 65% 时除以 100。"""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text or text.startswith("#"):
            return None
        has_percent = text.endswith("%")
        if has_percent:
            text = text[:-1].strip()
        try:
            number = parse_decimal(text)
        except (InvalidOperation, ValueError):
            return None
        if has_percent or number > Decimal("1"):
            number = number / Decimal("100")
        return quantize_money(number, Q4)
    try:
        number = parse_decimal(value)
    except (InvalidOperation, ValueError):
        return None
    if number > Decimal("1"):
        number = number / Decimal("100")
    return quantize_money(number, Q4)


def _field(
    sheet: Worksheet,
    lookup: dict[tuple[int, int], object],
    row: int,
    columns: DieColumnMap,
    key: str,
) -> object:
    col = columns.get(key)
    if not isinstance(col, int):
        return None
    return cell(sheet, lookup, row, col)


def parse_rows(
    sheet: Worksheet,
    lookup: dict[tuple[int, int], object],
    columns: DieColumnMap,
    data_start: int,
) -> list[ParsedDiePart]:
    parts: list[ParsedDiePart] = []
    by_part_number: dict[str, ParsedDiePart] = {}
    current: ParsedDiePart | None = None
    max_row = sheet.max_row or 0
    part_col = columns.get("part_number", 2)
    for row in range(data_start, max_row + 1):
        part_number = _text(_field(sheet, lookup, row, columns, "part_number"))
        process_seq = _text(_field(sheet, lookup, row, columns, "process_seq"))
        process_code = _text(_field(sheet, lookup, row, columns, "process_code"))
        if part_number:
            if "零件号" in part_number:
                continue
            existing = by_part_number.get(part_number)
            if existing is None:
                current = _part_from_row(sheet, lookup, row, part_number, columns, part_col)
                by_part_number[part_number] = current
                parts.append(current)
            else:
                current = existing
        if current is None:
            continue
        if not process_seq or process_seq in {"工序名称", "工序", "预估工艺"}:
            continue
        current.processes.append(
            ParsedDieProcess(
                process_seq=process_seq,
                process_code=process_code,
                die_sets=_as_int(_field(sheet, lookup, row, columns, "die_sets")),
                die_number=_text(_field(sheet, lookup, row, columns, "die_number")),
                die_length=_as_q2(_field(sheet, lookup, row, columns, "die_length")),
                die_width=_as_q2(_field(sheet, lookup, row, columns, "die_width")),
                die_height=_as_q2(_field(sheet, lookup, row, columns, "die_height")),
                hollow_factor=_as_q4(_field(sheet, lookup, row, columns, "hollow_factor")),
                estimated_weight_t=_as_q4(
                    _field(sheet, lookup, row, columns, "estimated_weight_t")
                ),
                tonnage=_as_int(_field(sheet, lookup, row, columns, "tonnage")),
                excel_row=row,
            )
        )
    return parts


def process_has_die_mass(process: ParsedDieProcess) -> bool:
    """本序有预估重量或任一外形尺寸，才可能算出模具费。"""
    weight = process.estimated_weight_t
    if weight is not None and weight > Decimal("0"):
        return True
    return any(
        value is not None and value > Decimal("0")
        for value in (process.die_length, process.die_width, process.die_height)
    )


def layout_has_die_mass(parts: list[ParsedDiePart]) -> bool:
    return any(process_has_die_mass(process) for part in parts for process in part.processes)


def _part_from_row(
    sheet: Worksheet,
    lookup: dict[tuple[int, int], object],
    row: int,
    part_number: str,
    columns: DieColumnMap,
    part_col: int,
) -> ParsedDiePart:
    part_weight = _as_q4(_field(sheet, lookup, row, columns, "part_weight"))
    sheet_length = _as_q2(_field(sheet, lookup, row, columns, "sheet_length"))
    sheet_width = _as_q2(_field(sheet, lookup, row, columns, "sheet_width"))
    sheet_shape = _text(_field(sheet, lookup, row, columns, "sheet_shape"))
    parts_per_sheet = _as_int(_field(sheet, lookup, row, columns, "parts_per_sheet"))
    return ParsedDiePart(
        seq_no=_as_int(_field(sheet, lookup, row, columns, "seq_no")),
        part_number=part_number,
        part_name=_text(_field(sheet, lookup, row, columns, "part_name")),
        material=_text(_field(sheet, lookup, row, columns, "material")),
        thickness=_as_q4(_field(sheet, lookup, row, columns, "thickness")),
        part_weight=part_weight,
        sheet_length=sheet_length,
        sheet_width=sheet_width,
        sheet_shape=sheet_shape,
        parts_per_sheet=parts_per_sheet,
        material_consumption=_as_q4(_field(sheet, lookup, row, columns, "material_consumption")),
        material_utilization=parse_unit_interval(
            _field(sheet, lookup, row, columns, "material_utilization")
        ),
        estimated_weight_subtotal_t=_as_q4(
            _field(sheet, lookup, row, columns, "estimated_weight_subtotal_t")
        ),
        die_type=_text(_field(sheet, lookup, row, columns, "die_type")),
        die_method=_collapse(_field(sheet, lookup, row, columns, "die_method")),
        production_mode=_text(_field(sheet, lookup, row, columns, "production_mode")),
        needs_end_effector=_text(_field(sheet, lookup, row, columns, "needs_end_effector")),
        part_grade=_text(_field(sheet, lookup, row, columns, "part_grade")),
        remark=_text(_field(sheet, lookup, row, columns, "remark")),
        excel_sheet_name=sheet.title,
        excel_row=row,
        excel_part_col=part_col,
        is_scrap_byproduct=layout_is_scrap_byproduct(
            part_number=part_number,
            part_weight=part_weight,
            sheet_length=sheet_length,
            sheet_width=sheet_width,
            parts_per_sheet=parts_per_sheet,
            raw_sheet_type=sheet_shape,
        ),
    )


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _collapse(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    return " ".join(text.split())


def _as_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.strip().startswith("#"):
        return None
    try:
        return int(parse_decimal(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _as_q2(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.strip().startswith("#"):
        return None
    try:
        return quantize_money(value, Q2)
    except (InvalidOperation, ValueError):
        return None


def _as_q4(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.strip().startswith("#"):
        return None
    try:
        return quantize_money(value, Q4)
    except (InvalidOperation, ValueError):
        return None
