"""冲压模具布点 Excel 解析（仅 A～AC，不抽图）。

列映射见 columns.py，行解析见 rows.py，类型见 types.py。
对外仍从此文件导入 parse_die_layout_excel 与类型。
"""

from __future__ import annotations

import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException

from .columns import (
    _HEADER_SCAN_ROWS,
    MAX_COL,
    build_merge_lookup,
    cell,
    find_header_rows,
    find_sheet,
    resolve_columns,
)
from .rows import layout_has_die_mass, parse_rows, parse_unit_interval, process_has_die_mass
from .types import DieColumnMap, DieParseResult, ParsedDiePart, ParsedDieProcess

_VEHICLE_TITLE_MARKERS = (
    "项目冲压模具布点工艺清单",
    "项目冲压模具布点工艺清",
    "项目冲压模具布点",
)
_COPY_PREFIX_RE = re.compile(r"^副本[①②③④⑤⑥⑦⑧⑨⑩]*")


def parse_die_layout_excel(file_path: str | Path, filename: str | None = None) -> DieParseResult:
    """解析模具布点清单。"""
    path = Path(file_path)
    workbook = load_workbook(path, data_only=True)
    try:
        sheet = find_sheet(workbook)
        header_lookup = build_merge_lookup(sheet, vertical_only=False, max_row=_HEADER_SCAN_ROWS)
        header_row, child_row, data_start = find_header_rows(sheet, header_lookup)
        columns = resolve_columns(sheet, header_lookup, header_row, child_row)
        if "part_number" not in columns:
            raise BusinessException("未识别到模具布点表头（需要「零件号」列）")
        if "process_seq" not in columns:
            raise BusinessException("未识别到「工序名称」列")
        data_lookup = build_merge_lookup(sheet, vertical_only=True, max_row=None)
        parts = parse_rows(sheet, data_lookup, columns, data_start)
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
            found = _vehicle_from_text(str(cell(sheet, lookup, row, col) or ""))
            if found:
                return found
    return None


__all__ = [
    "DieColumnMap",
    "DieParseResult",
    "ParsedDiePart",
    "ParsedDieProcess",
    "layout_has_die_mass",
    "parse_die_layout_excel",
    "parse_unit_interval",
    "process_has_die_mass",
]
