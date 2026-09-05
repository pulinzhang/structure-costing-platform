"""冲压模具布点 Excel 解析（仅 A～AC，不抽图）。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TypedDict

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.common.money import Q2, Q4, parse_decimal, quantize_money
from app.common.scrap_byproduct import layout_is_scrap_byproduct
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException

MAX_COL = 32  # 含模板插入的「模具编号」列；旧 A～AC 样本仍可解析
_HEADER_SCAN_ROWS = 12
_CHILD_HEADER_TOKENS = (
    "工序名称",
    "工序内容",
    "长度",
    "宽度",
    "高度",
    "模具长",
    "模具宽",
    "模具高",
)

_VEHICLE_TITLE_MARKERS = (
    "项目冲压模具布点工艺清单",
    "项目冲压模具布点工艺清",
    "项目冲压模具布点",
)


class DieColumnMap(TypedDict, total=False):
    seq_no: int
    part_number: int
    part_name: int
    material: int
    thickness: int
    part_weight: int
    sheet_length: int
    sheet_width: int
    sheet_shape: int
    parts_per_sheet: int
    material_consumption: int
    material_utilization: int
    process_seq: int
    process_code: int
    die_sets: int
    die_number: int
    die_length: int
    die_width: int
    die_height: int
    hollow_factor: int
    estimated_weight_t: int
    estimated_weight_subtotal_t: int
    tonnage: int
    die_type: int
    die_method: int
    production_mode: int
    needs_end_effector: int
    part_grade: int
    remark: int


@dataclass(slots=True)
class ParsedDieProcess:
    process_seq: str
    process_code: str | None
    die_sets: int | None
    die_number: str | None
    die_length: Decimal | None
    die_width: Decimal | None
    die_height: Decimal | None
    hollow_factor: Decimal | None
    estimated_weight_t: Decimal | None
    tonnage: int | None
    excel_row: int | None = None


@dataclass(slots=True)
class ParsedDiePart:
    seq_no: int | None
    part_number: str
    part_name: str | None
    material: str | None
    thickness: Decimal | None
    part_weight: Decimal | None
    sheet_length: Decimal | None
    sheet_width: Decimal | None
    sheet_shape: str | None
    parts_per_sheet: int | None
    material_consumption: Decimal | None
    material_utilization: Decimal | None
    estimated_weight_subtotal_t: Decimal | None
    die_type: str | None
    die_method: str | None
    production_mode: str | None
    needs_end_effector: str | None
    part_grade: str | None
    remark: str | None
    excel_sheet_name: str | None
    excel_row: int | None
    excel_part_col: int
    is_scrap_byproduct: bool = False
    processes: list[ParsedDieProcess] = field(default_factory=list)


@dataclass(slots=True)
class DieParseResult:
    vehicle_model: str | None
    sheet_name: str
    parts: list[ParsedDiePart]


def parse_die_layout_excel(file_path: str | Path, filename: str | None = None) -> DieParseResult:
    """解析模具布点清单。"""
    path = Path(file_path)
    workbook = load_workbook(path, data_only=True)
    try:
        sheet = _find_sheet(workbook)
        header_lookup = _build_merge_lookup(sheet, vertical_only=False, max_row=_HEADER_SCAN_ROWS)
        header_row, child_row, data_start = _find_header_rows(sheet, header_lookup)
        columns = _resolve_columns(sheet, header_lookup, header_row, child_row)
        if "part_number" not in columns:
            raise BusinessException("未识别到模具布点表头（需要「零件号」列）")
        if "process_seq" not in columns:
            raise BusinessException("未识别到「工序名称」列")
        data_lookup = _build_merge_lookup(sheet, vertical_only=True, max_row=None)
        parts = _parse_rows(sheet, data_lookup, columns, data_start)
        vehicle = _vehicle_from_text(filename or path.name)
        if vehicle is None:
            vehicle = _vehicle_from_sheet_title(sheet, header_lookup)
        return DieParseResult(
            vehicle_model=normalize_vehicle_model(vehicle) if vehicle else None,
            sheet_name=sheet.title,
            parts=parts,
        )
    finally:
        workbook.close()


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


def _find_sheet(workbook: Workbook) -> Worksheet:
    for candidate in workbook.worksheets:
        for row_idx in range(1, min(_HEADER_SCAN_ROWS, (candidate.max_row or 1) + 1)):
            for col in range(1, MAX_COL + 1):
                text = str(candidate.cell(row_idx, col).value or "")
                if "零件号" in text:
                    return candidate
    if not workbook.worksheets:
        raise BusinessException("Excel 没有工作表")
    return workbook.worksheets[0]


def _build_merge_lookup(
    sheet: Worksheet,
    *,
    vertical_only: bool,
    max_row: int | None,
) -> dict[tuple[int, int], object]:
    """
    vertical_only：只展开「同一列」的纵向合并，避免横向合并把模具方式灌进工序列。
    max_row：表头扫描时只收录落在该行及以内的合并。
    """
    lookup: dict[tuple[int, int], object] = {}
    for rng in sheet.merged_cells.ranges:
        if rng.min_col > MAX_COL:
            continue
        if max_row is not None and rng.min_row > max_row:
            continue
        if vertical_only and rng.min_col != rng.max_col:
            continue
        top = sheet.cell(rng.min_row, rng.min_col).value
        last_col = min(rng.max_col, MAX_COL)
        last_row = rng.max_row if max_row is None else min(rng.max_row, max_row)
        for row in range(rng.min_row, last_row + 1):
            for col in range(rng.min_col, last_col + 1):
                lookup[(row, col)] = top
    return lookup


def _cell(
    sheet: Worksheet,
    lookup: dict[tuple[int, int], object],
    row: int,
    col: int,
) -> object:
    if (row, col) in lookup:
        return lookup[(row, col)]
    return sheet.cell(row, col).value


def _find_header_rows(
    sheet: Worksheet,
    lookup: dict[tuple[int, int], object],
) -> tuple[int, int | None, int]:
    max_row = min(sheet.max_row or 1, _HEADER_SCAN_ROWS)
    for row in range(1, max_row + 1):
        for col in range(1, MAX_COL + 1):
            text = str(_cell(sheet, lookup, row, col) or "").replace("\n", "")
            if "零件号" not in text:
                continue
            child_row: int | None = None
            next_row = row + 1
            if next_row <= (sheet.max_row or 1):
                child_blob = "".join(
                    _compact(_cell(sheet, lookup, next_row, item)) for item in range(1, MAX_COL + 1)
                )
                if any(token in child_blob for token in _CHILD_HEADER_TOKENS):
                    child_row = next_row
            data_start = (child_row or row) + 1
            return row, child_row, data_start
    raise BusinessException("未识别到模具布点表头（需要「零件号」列）")


def _compact(value: object) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _column_path(
    sheet: Worksheet,
    lookup: dict[tuple[int, int], object],
    header_row: int,
    child_row: int | None,
    col: int,
) -> str:
    parent = _compact(_cell(sheet, lookup, header_row, col))
    child = _compact(_cell(sheet, lookup, child_row, col)) if child_row else ""
    if parent and child and child not in parent:
        return parent + child
    return parent or child


def _resolve_columns(
    sheet: Worksheet,
    lookup: dict[tuple[int, int], object],
    header_row: int,
    child_row: int | None,
) -> DieColumnMap:
    columns: DieColumnMap = {}
    taken: set[int] = set()

    def assign(key: str, col: int) -> None:
        if key not in columns and col not in taken:
            columns[key] = col  # type: ignore[literal-required]
            taken.add(col)

    paths = {
        col: _column_path(sheet, lookup, header_row, child_row, col)
        for col in range(1, MAX_COL + 1)
    }
    # 先匹配更具体的词，避免「长度」被「长」吃掉、工序列被「工序名称」吃掉。
    for col, path in paths.items():
        if not path or "简图" in path or "图片" in path:
            continue
        if "零件号" in path:
            assign("part_number", col)
        elif "零件名称" in path:
            assign("part_name", col)
        elif "工序名称" in path:
            assign("process_seq", col)
        elif "工序内容" in path:
            assign("process_code", col)
        elif path == "套数" or path.endswith("套数"):
            assign("die_sets", col)
        elif "模具编号" in path:
            assign("die_number", col)
        elif "模具长" in path:
            assign("die_length", col)
        elif "模具宽" in path:
            assign("die_width", col)
        elif "模具高" in path:
            assign("die_height", col)
        elif path == "工序" or path.endswith("工序"):
            assign("process_code", col)
        elif "掏空" in path:
            assign("hollow_factor", col)
        elif "重量小计" in path:
            assign("estimated_weight_subtotal_t", col)
        elif "预估重量" in path or "模具重量" in path:
            assign("estimated_weight_t", col)
        elif "吨位" in path:
            assign("tonnage", col)
        elif "模具类型" in path:
            assign("die_type", col)
        elif "模具方式" in path or "工艺方式" in path:
            assign("die_method", col)
        elif "生产方式" in path or "自动化" in path and "凸焊" not in path:
            assign("production_mode", col)
        elif "端拾器" in path:
            assign("needs_end_effector", col)
        elif "零件等级" in path or "难易度" in path:
            assign("part_grade", col)
        elif path == "备注" or path.endswith("备注"):
            assign("remark", col)
        elif "材质" in path or "牌号" in path:
            assign("material", col)
        elif "料厚" in path or "厚度" in path:
            assign("thickness", col)
        elif "净重" in path or "零件重量" in path:
            assign("part_weight", col)
        elif "板料形状" in path or "料片式样" in path:
            assign("sheet_shape", col)
        elif "可制" in path and "件" in path:
            assign("parts_per_sheet", col)
        elif "材料消耗" in path:
            assign("material_consumption", col)
        elif "利用率" in path:
            assign("material_utilization", col)
        elif path == "序号" or path.endswith("序号"):
            assign("seq_no", col)
        elif "长度" in path:
            assign("die_length", col)
        elif "宽度" in path:
            assign("die_width", col)
        elif "高度" in path:
            assign("die_height", col)
        elif "长" in path and ("板料" in path or "料片" in path or path.endswith("长")):
            assign("sheet_length", col)
        elif "宽" in path and ("板料" in path or "料片" in path or path.endswith("宽")):
            assign("sheet_width", col)
    return columns


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
    return _cell(sheet, lookup, row, col)


def _parse_rows(
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


_COPY_PREFIX_RE = re.compile(r"^副本[①②③④⑤⑥⑦⑧⑨⑩]*")


def _vehicle_from_text(text: str) -> str | None:
    compact = text.replace("\n", "").replace("\r", "").strip()
    if not compact:
        return None
    for marker in _VEHICLE_TITLE_MARKERS:
        idx = compact.find(marker)
        if idx > 0:
            prefix = _COPY_PREFIX_RE.sub("", compact[:idx]).strip(" -_—/\\")
            if prefix:
                return prefix
    return None


def _vehicle_from_sheet_title(
    sheet: Worksheet,
    lookup: dict[tuple[int, int], object],
) -> str | None:
    for row in range(1, 4):
        for col in range(1, MAX_COL + 1):
            found = _vehicle_from_text(str(_cell(sheet, lookup, row, col) or ""))
            if found:
                return found
    return None


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
