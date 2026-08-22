"""基准价格 summary / drivers。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.repositories.llm.base_price_analysis_repository import BasePricePeriodRow
from app.services.llm._money import money_str, month_key


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

    ranked = sorted(items, key=lambda item: Decimal(item["avg_base_price"]), reverse=True)[
        :top_n
    ]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}
