"""定价宽表：找工作表、认基地列、规格列、加工费列。"""

from __future__ import annotations

from typing import Any

from app.parsers.yishiyiyi.base_price.cells import cell_text
from app.parsers.yishiyiyi.base_price.models import BaseColumnConfig

_NON_LOCATION_HEADERS = frozenset({"合计", "厚度加减价", "未税合计", "含税合计"})
_PREFERRED_SHEETS = ("Sheet1", "发布价汇总价", "总价格", "汇总价格")
_DATA_START_COL = 4
DEFAULT_SPEC_COL = 3
DEFAULT_FEE_COL = 8


def find_data_sheet(workbook: Any) -> Any | None:
    for name in _PREFERRED_SHEETS:
        if name not in workbook.sheetnames:
            continue
        sheet = workbook[name]
        if _sheet_has_steel_headers(sheet):
            return sheet
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        if _row_has_any_keyword(sheet, (4, 5), ("钢种", "牌号", "规格", "钢厂", "价格")):
            return sheet
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        if _row6_has_values(sheet):
            return sheet
    return None


def extract_base_configs(
    sheet: Any, location_lookup: dict[str, str]
) -> tuple[list[BaseColumnConfig], list[str]]:
    """
    第4行基地名、第5行子标题。
    有「钢厂」列时只走钢厂+价格对；没有钢厂列才按价格列认基地。
    lookup 未命中记入 skipped，不进 configs。
    """
    header_row = next(iter(sheet.iter_rows(min_row=4, max_row=4, values_only=True)))
    sub_row = next(iter(sheet.iter_rows(min_row=5, max_row=5, values_only=True)))
    configs: list[BaseColumnConfig] = []
    skipped: list[str] = []
    saw_mill_col = False

    def accept(base_name: str, mill_col: int, price_col: int) -> None:
        location = location_lookup.get(base_name.strip()) if base_name.strip() else None
        if location is None:
            if base_name not in _NON_LOCATION_HEADERS and base_name not in skipped:
                skipped.append(base_name)
            return
        configs.append(BaseColumnConfig(location=location, mill_col=mill_col, price_col=price_col))

    for idx in range(_DATA_START_COL, len(header_row)):
        base_name = cell_text(header_row[idx])
        sub_text = cell_text(sub_row[idx]) if idx < len(sub_row) else ""
        if not base_name or not _is_mill_subtitle(sub_text):
            continue
        saw_mill_col = True
        price_col = _look_ahead_price_col(header_row, sub_row, idx, base_name)
        if price_col is not None:
            accept(base_name, idx, price_col)

    if not saw_mill_col:
        _scan_price_only_columns(header_row, sub_row, accept)

    return configs, skipped


def find_spec_column(sheet: Any) -> int | None:
    for row_idx in (4, 5):
        try:
            header_row = next(
                iter(sheet.iter_rows(min_row=row_idx, max_row=row_idx, values_only=True))
            )
        except (IndexError, StopIteration):
            continue
        for col_idx, cell in enumerate(header_row):
            cell_str = cell_text(cell)
            if not cell_str:
                continue
            if "参考规格" in cell_str:
                return col_idx
            if "规格" in cell_str and len(cell_str) <= 10:
                return col_idx
    return None


def find_processing_fee_col(sheet: Any) -> int | None:
    for row_idx in (4, 5):
        header_row = next(iter(sheet.iter_rows(min_row=row_idx, max_row=row_idx, values_only=True)))
        for idx, cell in enumerate(header_row):
            if cell and "加工费" in str(cell):
                return idx
    return None


def _is_mill_subtitle(sub_text: str) -> bool:
    return bool(sub_text) and ("中标钢厂" in sub_text or "钢厂" in sub_text)


def _is_price_subtitle(sub_text: str) -> bool:
    return bool(sub_text) and ("价格" in sub_text or "承兑" in sub_text)


def _look_ahead_price_col(
    header_row: Any, sub_row: Any, mill_idx: int, base_name: str
) -> int | None:
    for lookahead in range(mill_idx + 1, len(header_row)):
        lookahead_sub = cell_text(sub_row[lookahead]) if lookahead < len(sub_row) else ""
        if _is_price_subtitle(lookahead_sub):
            return lookahead
        next_base = cell_text(header_row[lookahead])
        if next_base and next_base != base_name:
            return None
    return None


def _scan_price_only_columns(header_row: Any, sub_row: Any, accept: Any) -> None:
    for idx in range(_DATA_START_COL, len(header_row)):
        base_name = cell_text(header_row[idx])
        sub_text = cell_text(sub_row[idx]) if idx < len(sub_row) else ""
        if not base_name:
            continue
        if _is_price_subtitle(sub_text):
            accept(base_name, idx, idx)
            continue
        if sub_text or base_name in _NON_LOCATION_HEADERS:
            continue
        price_col = _look_ahead_price_col(header_row, sub_row, idx, base_name)
        if price_col is not None:
            accept(base_name, idx, price_col)


def _sheet_has_steel_headers(sheet: Any) -> bool:
    try:
        row4 = next(iter(sheet.iter_rows(min_row=4, max_row=4, values_only=True)))
        row5 = next(iter(sheet.iter_rows(min_row=5, max_row=5, values_only=True)))
    except (IndexError, StopIteration):
        return False
    header_text = " ".join(cell_text(cell) for cell in row4 + row5 if cell)
    return "钢种" in header_text or "牌号" in header_text


def _row_has_any_keyword(
    sheet: Any, row_indexes: tuple[int, ...], keywords: tuple[str, ...]
) -> bool:
    for row_idx in row_indexes:
        try:
            header_row = next(
                iter(sheet.iter_rows(min_row=row_idx, max_row=row_idx, values_only=True))
            )
        except (IndexError, StopIteration):
            continue
        header_text = " ".join(cell_text(cell) for cell in header_row if cell)
        if any(keyword in header_text for keyword in keywords):
            return True
    return False


def _row6_has_values(sheet: Any) -> bool:
    try:
        first_data_row = next(iter(sheet.iter_rows(min_row=6, max_row=6, values_only=True)))
    except (IndexError, StopIteration):
        return False
    return any(cell is not None and cell_text(cell) for cell in first_data_row[:5])
