"""中标厚度价格一览 Excel — 列布局、溯源文案、摘录行挑选。"""

from __future__ import annotations

from decimal import Decimal

from app.common.money import Q2, quantize_money
from app.schemas.vo.winning_thickness_vo import WinningThicknessRowVO

DOC_TITLE = "中标钢厂厚度价格列表"
DOC_ORG = "结构件自动核价平台"
PRICE_UNIT = "元/吨"

OVERVIEW_SHEET_SUFFIX = "厚度价格列表"
CALC_SHEET_SUFFIX = "计算用"
EXAMPLE_SHEET_SUFFIX = "使用示例"

_SHEET_NAME_MAX = 31
_SHEET_NAME_INVALID = frozenset(":\\/?*[]")

TABLE_HEADER_ROW = 6
EXAMPLE_ROW_LIMIT = 5

OVERVIEW_HEADERS = [
    "基地/钢种",
    "牌号",
    "钢厂",
    "厚度范围",
    "基准价(元/吨)",
    "加减价(元/吨)",
    "加工费(元/吨)",
    "最终价(元/吨)",
    "基价溯源",
    "厚度溯源",
]
OVERVIEW_COLUMN_WIDTHS = [18, 14, 12, 18, 14, 14, 14, 16, 36, 36]
OVERVIEW_WEAK_COLS = frozenset({1, 9, 10})
OVERVIEW_PRICE_COLS = frozenset({5, 6, 7, 8})
OVERVIEW_FINAL_COL = 8
OVERVIEW_TAB_COLOR = "1F4E79"

CALC_HEADERS = [
    "基地",
    "钢种",
    "牌号",
    "钢厂",
    "厚min",
    "下限符号",
    "厚max",
    "上限符号",
    "厚度范围",
    "基准价(元/吨)",
    "加减价(元/吨)",
    "加工费(元/吨)",
    "最终价(元/吨)",
]
# E–H 供公式匹配，导出时隐藏；读者只看 A–D、I–M
CALC_COLUMN_WIDTHS = [14, 14, 14, 12, 10, 12, 10, 12, 18, 14, 14, 14, 16]
CALC_HIDDEN_COLS = frozenset({5, 6, 7, 8})
CALC_PRICE_COLS = frozenset({10, 11, 12, 13})
CALC_OPERATOR_COLS = frozenset({6, 8})
CALC_NUMBER_COLS = frozenset({5, 7, 10, 11, 12, 13})
CALC_THICK_COLS = frozenset({5, 7})
CALC_FINAL_COL = 13
CALC_TAB_COLOR = "548235"
EXAMPLE_TAB_COLOR = "C65911"


def format_location_category(location: str | None, category_name: str | None) -> str:
    loc = (location or "").strip()
    cat = (category_name or "").strip()
    if loc and cat:
        return f"{loc} · {cat}"
    return loc or cat or ""


def format_base_trace(row: WinningThicknessRowVO) -> str:
    parts = []
    if row.base_price_id is not None:
        parts.append(f"ID:{row.base_price_id}")
    if row.base_excel_filename:
        parts.append(row.base_excel_filename)
    if row.base_sheet_name:
        parts.append(row.base_sheet_name)
    if row.base_excel_row is not None:
        parts.append(f"R{row.base_excel_row}")
    if row.base_excel_col is not None:
        parts.append(f"C{row.base_excel_col}")
    return " · ".join(parts)


def format_thickness_trace(row: WinningThicknessRowVO) -> str:
    parts = []
    if row.thickness_policy_id is not None:
        parts.append(f"P:{row.thickness_policy_id}")
    if row.thickness_ladder_item_id is not None:
        parts.append(f"L:{row.thickness_ladder_item_id}")
    if row.thickness_excel_filename:
        parts.append(row.thickness_excel_filename)
    if row.thickness_steel_mill:
        parts.append(row.thickness_steel_mill)
    if row.thickness_sheet_name:
        parts.append(row.thickness_sheet_name)
    if row.thickness_excel_row is not None:
        parts.append(f"R{row.thickness_excel_row}")
    if row.thickness_excel_col is not None:
        parts.append(f"C{row.thickness_excel_col}")
    return " · ".join(parts)


def excel_operator(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def excel_thickness(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return quantize_money(value, Q2)


def filter_rows_for_export(rows: list[WinningThicknessRowVO]) -> list[WinningThicknessRowVO]:
    """仅保留有基价溯源的行；未定基价的不进入 Excel。"""
    return [row for row in rows if row.base_price_id is not None]


def pick_example_rows(rows: list[WinningThicknessRowVO]) -> list[WinningThicknessRowVO]:
    rows = filter_rows_for_export(rows)
    if not rows:
        return []
    bounded = [row for row in rows if row.thick_min is not None or row.thick_max is not None]
    primary = bounded or rows
    picked: list[WinningThicknessRowVO] = []
    seen: set[tuple[str, str]] = set()
    for row in primary:
        key = ((row.grade or "").strip(), (row.steel_mill or "").strip())
        if key in seen:
            continue
        seen.add(key)
        picked.append(row)
        if len(picked) >= EXAMPLE_ROW_LIMIT:
            return picked
    picked_ids = {id(row) for row in picked}
    for pool in (primary, rows):
        for row in pool:
            if id(row) in picked_ids:
                continue
            picked.append(row)
            picked_ids.add(id(row))
            if len(picked) >= EXAMPLE_ROW_LIMIT:
                return picked
    return picked


def thickness_in_interval(thickness: Decimal, row: WinningThicknessRowVO) -> bool:
    if row.thick_min is not None:
        operator = (row.thick_min_operator or ">=").strip()
        if operator == ">=" and not (thickness >= row.thick_min):
            return False
        if operator == ">" and not (thickness > row.thick_min):
            return False
    if row.thick_max is not None:
        operator = (row.thick_max_operator or "<").strip()
        if operator == "<=" and not (thickness <= row.thick_max):
            return False
        if operator == "<" and not (thickness < row.thick_max):
            return False
    return True


def sample_thickness(row: WinningThicknessRowVO) -> Decimal | None:
    min_value = row.thick_min
    max_value = row.thick_max
    candidates: list[Decimal] = []
    if min_value is not None and max_value is not None:
        candidates.append(
            ((Decimal(str(min_value)) + Decimal(str(max_value))) / Decimal("2")).quantize(Q2)
        )
    if min_value is not None:
        candidates.append(Decimal(str(min_value)))
        candidates.append((Decimal(str(min_value)) + Q2).quantize(Q2))
    if max_value is not None:
        candidates.append(Decimal(str(max_value)))
        lower = Decimal(str(max_value)) - Q2
        if lower > 0:
            candidates.append(lower.quantize(Q2))
    for candidate in candidates:
        if thickness_in_interval(candidate, row):
            return candidate
    return None


def scoped_sheet_name(
    *,
    year: int | None,
    month: int | None,
    location: str | None,
    suffix: str,
) -> str:
    loc = "".join(ch for ch in (location or "").strip() if ch not in _SHEET_NAME_INVALID)
    bits: list[str] = []
    if year is not None and month is not None:
        bits.append(f"{year}年{month}月")
    elif year is not None:
        bits.append(f"{year}年")
    if loc:
        bits.append(loc)
    prefix = "".join(bits) or "全部"
    name = f"{prefix}_{suffix}"
    return name[:_SHEET_NAME_MAX]


def excel_sheet_ref(sheet_name: str) -> str:
    escaped = sheet_name.replace("'", "''")
    return f"'{escaped}'"


def build_filename(*, year: int | None, month: int | None, location: str | None) -> str:
    parts = [DOC_TITLE]
    if year is not None and month is not None:
        parts.append(f"{year}年_{month}月")
    elif year is not None:
        parts.append(f"{year}年")
    if location:
        parts.append(location)
    return "_".join(parts) + ".xlsx"


def format_period_label(*, year: int | None, month: int | None, location: str | None = None) -> str:
    bits: list[str] = []
    if location:
        bits.append(location)
    if year is not None and month is not None:
        bits.append(f"{year}年{month}月")
    elif year is not None:
        bits.append(f"{year}年")
    return " ".join(bits) if bits else "全部"
