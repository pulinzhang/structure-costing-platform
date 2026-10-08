"""牌号厚度价行表。口径与中标厚度列表相同：基价 × 厚度阶梯，不看冲压件。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.schemas.llm.analysis_payload import DomainAnomaliesPayload
from app.services.llm._money import money_str

_LIST_CAP = 200
_TABLE_COLUMNS = (
    "period",
    "location",
    "steel_mill",
    "category_name",
    "grade",
    "thickness_range",
    "base_price",
    "thickness_adjustment",
    "processing_fee",
    "final_price",
)


@dataclass(frozen=True, slots=True)
class GradeThicknessPriceRow:
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thickness_range: str
    thick_min: Decimal | None
    thick_min_operator: str | None
    thick_max: Decimal | None
    thick_max_operator: str | None
    base_price: Decimal
    thickness_adjustment: Decimal
    processing_fee: Decimal
    final_price: Decimal


def thickness_in_band(thickness: Decimal, row: GradeThicknessPriceRow) -> bool:
    """料厚是否落在该厚度档。运算符与厚度阶梯匹配一致。"""
    if row.thick_min is not None:
        op = (row.thick_min_operator or ">=").strip()
        if op == ">=" and thickness < row.thick_min:
            return False
        if op == ">" and thickness <= row.thick_min:
            return False
    if row.thick_max is not None:
        op = (row.thick_max_operator or "<").strip()
        if op == "<=" and thickness > row.thick_max:
            return False
        if op == "<" and thickness >= row.thick_max:
            return False
    return True


def build_steel_price_rows(rows: list[GradeThicknessPriceRow]) -> DomainAnomaliesPayload:
    ordered = sorted(rows, key=_sort_key)
    truncated = len(ordered) > _LIST_CAP
    shown = ordered[:_LIST_CAP]
    note = (
        f"钢材价格 {len(shown)} 条。"
        "按中标基价和厚度阶梯展开，不看冲压件实际用料。"
        "已按年、月、基地、牌号、厚度档排好。"
        "联动价等于基准价加厚度加减价加加工费，不要再加一次。"
        "多行是基地、钢厂或厚度档不同，不要收成一个数。"
    )
    if truncated:
        note += f"这里只列出前 {_LIST_CAP} 条。"
    items = [_row_item(row, order=index) for index, row in enumerate(shown, start=1)]
    return {
        "kind": "steel_price_rows",
        "count": len(shown),
        "note": note,
        "lines": [item["line"] for item in items],
        "table": render_steel_price_rows_table(items),
        "items": items,
        "subject": "steel_price",
    }


def render_steel_price_rows_table(items: Sequence[object]) -> str:
    header = (
        "| 年月 | 基地 | 钢厂 | 大类 | 牌号 | 厚度档 | "
        "基准价（元/吨） | 厚度加减价（元/吨） | 加工费（元/吨） | 联动价（元/吨） |"
    )
    rows = [
        header,
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    written = 0
    for item in items:
        if not isinstance(item, Mapping):
            continue
        cells = [_table_cell(item, key) for key in _TABLE_COLUMNS]
        rows.append("| " + " | ".join(cells) + " |")
        written += 1
    if written == 0:
        return ""
    return "\n".join(rows)


def _sort_key(
    row: GradeThicknessPriceRow,
) -> tuple[int, int, str, str, str, Decimal, str]:
    thick_min = row.thick_min if row.thick_min is not None else Decimal("-1")
    return (
        row.year,
        row.month,
        row.location,
        row.category_name,
        row.grade,
        thick_min,
        row.steel_mill,
    )


def _row_item(row: GradeThicknessPriceRow, *, order: int) -> dict[str, str]:
    period = f"{row.year:04d}年{row.month:02d}月"
    base_price = money_str(row.base_price)
    thickness_adjustment = money_str(row.thickness_adjustment)
    processing_fee = money_str(row.processing_fee)
    final_price = money_str(row.final_price)
    line = (
        f"{period} {row.location} {row.steel_mill} {row.category_name} "
        f"{row.grade} {row.thickness_range}，"
        f"基准价 {base_price} 元/吨，厚度加减价 {thickness_adjustment} 元/吨，"
        f"加工费 {processing_fee} 元/吨，联动价 {final_price} 元/吨"
    )
    return {
        "order": str(order),
        "period": period,
        "location": row.location,
        "steel_mill": row.steel_mill,
        "category_name": row.category_name,
        "grade": row.grade,
        "thickness_range": row.thickness_range,
        "base_price": base_price,
        "thickness_adjustment": thickness_adjustment,
        "processing_fee": processing_fee,
        "final_price": final_price,
        "line": line,
    }


def _table_cell(item: Mapping[str, object], key: str) -> str:
    value = item.get(key)
    text = "" if value is None else str(value)
    return text.replace("|", "｜")
