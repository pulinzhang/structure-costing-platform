"""基准价格 summary / trend / 月度异常。"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.repositories.llm.base_price_analysis_repository import BasePricePeriodRow
from app.schemas.llm.analysis_payload import (
    DomainAnomaliesPayload,
    DriverItem,
    DriversPayload,
    MomAnomalyItem,
    SummaryPayload,
    TrendPayload,
)
from app.schemas.llm.analysis_query import ComparisonBasis
from app.services.llm._money import money_str, month_key
from app.services.llm.analysis.shared.cost_trend import trend_from_series


def build_base_price_summary(rows: list[BasePricePeriodRow]) -> SummaryPayload:
    if not rows:
        return {
            "subject": "steel_base_price",
            "row_count": 0,
            "location_count": 0,
            "steel_mill_count": 0,
            "avg_base_price": "0.0000",
            "avg_processing_fee": "0.0000",
            "months": [],
        }

    locations = {row.location for row in rows}
    mills = {row.steel_mill_id for row in rows}
    base_sum = sum((row.base_price for row in rows), start=Decimal("0"))
    fee_sum = sum((row.processing_fee for row in rows), start=Decimal("0"))
    count = Decimal(len(rows))
    by_month: dict[str, int] = defaultdict(int)
    for row in rows:
        by_month[month_key(row.year, row.month)] += 1

    return {
        "subject": "steel_base_price",
        "row_count": len(rows),
        "location_count": len(locations),
        "steel_mill_count": len(mills),
        "avg_base_price": money_str(base_sum / count),
        "avg_processing_fee": money_str(fee_sum / count),
        "months": [
            {"month": month, "row_count": row_count}
            for month, row_count in sorted(by_month.items())
        ],
    }


def build_base_price_drivers(rows: list[BasePricePeriodRow], *, top_n: int = 15) -> DriversPayload:
    """按 steel_mill_id 汇总。钢厂字用结果行上的字。"""
    by_mill: dict[int, list[BasePricePeriodRow]] = defaultdict(list)
    for row in rows:
        by_mill[row.steel_mill_id].append(row)

    items: list[DriverItem] = []
    for _mill_id, mill_rows in by_mill.items():
        prices = [row.base_price for row in mill_rows]
        avg = sum(prices, start=Decimal("0")) / Decimal(len(prices))
        items.append(
            {
                "object_type": "steel_base_price",
                "steel_mill": mill_rows[0].steel_mill,
                "row_count": len(mill_rows),
                "avg_base_price": money_str(avg),
                "max_base_price": money_str(max(prices)),
            }
        )

    ranked = sorted(items, key=lambda item: Decimal(str(item["avg_base_price"])), reverse=True)[
        :top_n
    ]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}


def build_base_price_trend(
    rows: list[BasePricePeriodRow],
    *,
    basis: ComparisonBasis,
) -> TrendPayload:
    """各月基准价均值序列（看整体上下波动）。"""
    by_month: dict[str, list[Decimal]] = defaultdict(list)
    for row in rows:
        by_month[month_key(row.year, row.month)].append(row.base_price)

    series = [
        (
            month,
            sum(prices, start=Decimal("0")) / Decimal(len(prices)),
        )
        for month, prices in sorted(by_month.items())
    ]
    trend = trend_from_series(series, value_label="avg_base_price", basis=basis)
    trend["subject"] = "steel_base_price"
    return trend


def _base_price_series_key(row: BasePricePeriodRow) -> str:
    return f"{row.location}|{row.steel_mill_id}|{row.category_name}|{row.grade}|{row.spec}"


def build_base_price_mom_anomalies(
    rows: list[BasePricePeriodRow],
    *,
    top_n: int = 15,
    min_abs_change: Decimal = Decimal("50"),
    min_rate: Decimal = Decimal("0.03"),
) -> DomainAnomaliesPayload:
    """同 steel_mill_id、牌号、规格的基准价跳变。清单按月份从早到晚。钢厂字用结果行上的字。"""
    by_key: dict[str, dict[str, BasePricePeriodRow]] = defaultdict(dict)
    for row in rows:
        month = month_key(row.year, row.month)
        key = _base_price_series_key(row)
        existing = by_key[key].get(month)
        if existing is None:
            by_key[key][month] = row
            continue
        merged_price = (existing.base_price + row.base_price) / Decimal("2")
        by_key[key][month] = BasePricePeriodRow(
            year=row.year,
            month=row.month,
            location=row.location,
            steel_mill=row.steel_mill,
            steel_mill_id=row.steel_mill_id,
            category_name=row.category_name,
            grade=row.grade,
            spec=row.spec,
            base_price=merged_price,
            processing_fee=(existing.processing_fee + row.processing_fee) / Decimal("2"),
        )

    spikes: list[MomAnomalyItem] = []
    for _key, month_map in by_key.items():
        ordered_months = sorted(month_map.keys())
        ordered_rows = [month_map[month] for month in ordered_months]
        for index in range(1, len(ordered_rows)):
            prev_row = ordered_rows[index - 1]
            curr_row = ordered_rows[index]
            change = curr_row.base_price - prev_row.base_price
            rate: Decimal | None = None
            if prev_row.base_price != 0:
                rate = (change / prev_row.base_price).quantize(Decimal("0.0001"))
            if abs(change) < min_abs_change and (rate is None or abs(rate) < min_rate):
                continue
            spikes.append(
                {
                    "anomaly_type": "base_price_jump",
                    "location": curr_row.location,
                    "steel_mill": curr_row.steel_mill,
                    "category_name": curr_row.category_name,
                    "grade": curr_row.grade,
                    "spec": curr_row.spec,
                    "month": month_key(curr_row.year, curr_row.month),
                    "prev_month": month_key(prev_row.year, prev_row.month),
                    "prev_base_price": money_str(prev_row.base_price),
                    "curr_base_price": money_str(curr_row.base_price),
                    "change": money_str(change),
                    "change_rate": str(rate) if rate is not None else None,
                    "hint": "环比跳变较大，建议核对是否上传错月或错价",
                }
            )

    picked = sorted(
        spikes,
        key=lambda item: (
            abs(Decimal(item["change"] or "0")),
            abs(Decimal(item["change_rate"] or "0")),
        ),
        reverse=True,
    )[:top_n]
    picked.sort(key=lambda item: str(item.get("month") or ""))
    for index, item in enumerate(picked, start=1):
        item["rank"] = index
    return {
        "kind": "base_price_anomalies",
        "items": picked,
        "top_n": top_n,
        "subject": "steel_base_price",
    }


_Q2 = Decimal("0.01")
_MONTH_MOVE_LIST_CAP = 200


@dataclass(frozen=True, slots=True)
class _MonthMove:
    row: BasePricePeriodRow
    previous: BasePricePeriodRow
    delta: Decimal


def build_base_price_month_move_over(
    rows: list[BasePricePeriodRow],
    *,
    limit: Decimal,
    window_start: tuple[int, int],
) -> DomainAnomaliesPayload:
    """单价加加工费相对上月同基地。大于 limit 才列出，等于不算。"""
    by_period: dict[tuple[int, int], list[BasePricePeriodRow]] = defaultdict(list)
    for row in rows:
        if row.thick is None or row.width is None:
            continue
        by_period[(row.year, row.month)].append(row)

    found: list[_MonthMove] = []
    for year, month in sorted(by_period):
        if (year, month) < window_start:
            continue
        previous_rows = by_period.get(_previous_period(year, month), [])
        grouped: dict[tuple[str, str, Decimal, Decimal], list[BasePricePeriodRow]] = defaultdict(
            list
        )
        for previous in previous_rows:
            key = _month_move_key(previous)
            if key is not None:
                grouped[key].append(previous)
        for row in by_period[(year, month)]:
            key = _month_move_key(row)
            if key is None:
                continue
            counterpart = _counterpart(row, grouped.get(key, []))
            if counterpart is None:
                continue
            delta = _landed(row) - _landed(counterpart)
            if abs(delta) <= limit:
                continue
            found.append(_MonthMove(row=row, previous=counterpart, delta=delta))

    found.sort(
        key=lambda item: (
            item.row.year,
            item.row.month,
            item.row.location,
            item.row.grade,
            item.row.spec,
        )
    )
    shown = found[:_MONTH_MOVE_LIST_CAP]
    limit_text = money_str(limit)
    note = (
        f"单价加加工费相对上月同基地，大于 {limit_text} 元/吨的有 {len(found)} 条。"
        "等于这个数不算。清单已按年、月、基地、牌号排好，回答时按这个顺序写。"
    )
    if len(found) > len(shown):
        note += f"这里只列出前 {len(shown)} 条。"
    if not found:
        note = f"单价加加工费相对上月同基地，大于 {limit_text} 元/吨的没有。等于这个数不算。"
    items = [_month_move_item(item, order=index) for index, item in enumerate(shown, start=1)]
    return {
        "kind": "base_price_month_move_over",
        "count": len(found),
        "threshold": limit_text,
        "note": note,
        "lines": [item["line"] for item in items],
        "table": render_base_price_month_move_table(items),
        "items": items,
        "subject": "steel_base_price",
    }


_TABLE_COLUMNS = (
    "period",
    "location",
    "grade",
    "spec",
    "steel_mill",
    "previous_steel_mill",
    "base_price",
    "previous_base_price",
    "change",
)


def render_base_price_month_move_table(items: Sequence[object]) -> str:
    """按 items 既有顺序画表。这个顺序是年、月、基地、牌号。"""
    rows = [
        "| 年月 | 基地 | 牌号 | 规格 | 本月钢厂 | 上月钢厂 | 本月基准价（元/吨） | 上月基准价（元/吨） | 变动（元/吨） |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
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


def _table_cell(item: Mapping[str, object], key: str) -> str:
    value = item.get(key)
    text = "" if value is None else str(value)
    return text.replace("|", "｜")


def _previous_period(year: int, month: int) -> tuple[int, int]:
    if month <= 1:
        return year - 1, 12
    return year, month - 1


def _month_move_key(row: BasePricePeriodRow) -> tuple[str, str, Decimal, Decimal] | None:
    """基地 + 牌号 + 参考厚度 + 参考宽度。规格不全则对不上上月。"""
    if row.thick is None or row.width is None:
        return None
    return (
        row.location,
        row.grade,
        row.thick.quantize(_Q2, rounding=ROUND_HALF_UP),
        row.width.quantize(_Q2, rounding=ROUND_HALF_UP),
    )


def _landed(row: BasePricePeriodRow) -> Decimal:
    return (row.base_price + row.processing_fee).quantize(_Q2, rounding=ROUND_HALF_UP)


def _counterpart(
    row: BasePricePeriodRow,
    group: list[BasePricePeriodRow],
) -> BasePricePeriodRow | None:
    """同一 steel_mill_id 对上月那一条。上月这一规格只有一条时，钢厂换了也对照。多家则不猜。"""
    same_mill = [item for item in group if item.steel_mill_id == row.steel_mill_id]
    if len(same_mill) == 1:
        return same_mill[0]
    if same_mill:
        return None
    if len(group) == 1:
        return group[0]
    return None


def _signed_money(value: Decimal) -> str:
    text = money_str(value)
    if text.startswith("-"):
        return text
    return f"+{text}"


def _month_move_item(item: _MonthMove, *, order: int) -> dict[str, str]:
    row = item.row
    previous = item.previous
    change = _signed_money(item.delta)
    period = f"{row.year:04d}年{row.month:02d}月"
    base_price = money_str(row.base_price)
    previous_base_price = money_str(previous.base_price)
    line = (
        f"{period} {row.location} {row.grade} {row.spec}，"
        f"本月钢厂{row.steel_mill}，上月钢厂{previous.steel_mill}，"
        f"本月基准价 {base_price} 元/吨，变动 {change} 元/吨"
    )
    return {
        "order": str(order),
        "period": period,
        "location": row.location,
        "grade": row.grade,
        "spec": row.spec,
        "steel_mill": row.steel_mill,
        "previous_steel_mill": previous.steel_mill,
        "base_price": base_price,
        "previous_base_price": previous_base_price,
        "change": change,
        "line": line,
    }
