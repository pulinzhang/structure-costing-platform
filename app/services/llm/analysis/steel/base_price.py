"""基准价格 summary / trend / 月度异常。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.repositories.llm.base_price_analysis_repository import BasePricePeriodRow
from app.schemas.llm.analysis_query import ComparisonBasis
from app.services.llm._money import money_str, month_key
from app.services.llm.analysis.shared.cost_trend import _trend_from_series


def build_base_price_summary(rows: list[BasePricePeriodRow]) -> dict[str, Any]:
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
    mills = {row.steel_mill for row in rows}
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


def build_base_price_drivers(rows: list[BasePricePeriodRow], *, top_n: int = 15) -> dict[str, Any]:
    by_mill: dict[str, list[BasePricePeriodRow]] = defaultdict(list)
    for row in rows:
        by_mill[row.steel_mill].append(row)

    items: list[dict[str, Any]] = []
    for mill, mill_rows in by_mill.items():
        prices = [row.base_price for row in mill_rows]
        avg = sum(prices, start=Decimal("0")) / Decimal(len(prices))
        items.append(
            {
                "object_type": "steel_base_price",
                "steel_mill": mill,
                "row_count": len(mill_rows),
                "avg_base_price": money_str(avg),
                "max_base_price": money_str(max(prices)),
            }
        )

    ranked = sorted(items, key=lambda item: Decimal(item["avg_base_price"]), reverse=True)[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}


def build_base_price_trend(
    rows: list[BasePricePeriodRow],
    *,
    basis: ComparisonBasis,
) -> dict[str, Any]:
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
    trend = _trend_from_series(series, value_label="avg_base_price", basis=basis)
    trend["subject"] = "steel_base_price"
    return trend


def _base_price_series_key(row: BasePricePeriodRow) -> str:
    return f"{row.location}|{row.steel_mill}|{row.category_name}|{row.grade}|{row.spec}"


def build_base_price_mom_anomalies(
    rows: list[BasePricePeriodRow],
    *,
    top_n: int = 15,
    min_abs_change: Decimal = Decimal("50"),
    min_rate: Decimal = Decimal("0.03"),
) -> dict[str, Any]:
    """同钢厂/牌号/规格在各月间的基准价跳变（疑似传错价）。"""
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
            category_name=row.category_name,
            grade=row.grade,
            spec=row.spec,
            base_price=merged_price,
            processing_fee=(existing.processing_fee + row.processing_fee) / Decimal("2"),
        )

    spikes: list[dict[str, Any]] = []
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

    ranked = sorted(
        spikes,
        key=lambda item: (
            abs(Decimal(item["change"] or "0")),
            abs(Decimal(item["change_rate"] or "0")),
        ),
        reverse=True,
    )[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {
        "kind": "base_price_anomalies",
        "items": ranked,
        "top_n": top_n,
        "subject": "steel_base_price",
    }
