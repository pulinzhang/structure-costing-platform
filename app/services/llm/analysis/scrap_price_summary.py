"""废料月度销售价 summary / drivers。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.repositories.llm.scrap_price_analysis_repository import ScrapPricePeriodRow
from app.services.llm._money import month_key


def _scrap_price_str(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def build_scrap_price_summary(rows: list[ScrapPricePeriodRow]) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "scrap_price",
            "row_count": 0,
            "location_count": 0,
            "avg_net_price": "0.00",
            "months": [],
        }

    locations = {row.location for row in rows}
    net_sum = sum((row.net_price for row in rows), start=Decimal("0"))
    count = Decimal(len(rows))
    by_month: dict[str, list[ScrapPricePeriodRow]] = defaultdict(list)
    for row in rows:
        by_month[month_key(row.year, row.month)].append(row)

    return {
        "subject": "scrap_price",
        "row_count": len(rows),
        "location_count": len(locations),
        "avg_net_price": _scrap_price_str(net_sum / count),
        "months": [
            {
                "month": month,
                "row_count": len(items),
                "avg_net_price": _scrap_price_str(
                    sum((item.net_price for item in items), start=Decimal("0"))
                    / Decimal(len(items)),
                ),
            }
            for month, items in sorted(by_month.items())
        ],
    }


def build_scrap_price_drivers(
    rows: list[ScrapPricePeriodRow],
    *,
    top_n: int = 6,
) -> dict[str, Any]:
    """按基地汇总当月净价（固定 6 行矩阵，取有数据的基地）。"""
    by_location: dict[str, list[ScrapPricePeriodRow]] = defaultdict(list)
    for row in rows:
        by_location[row.location].append(row)

    items: list[dict[str, Any]] = []
    for location, location_rows in by_location.items():
        latest = sorted(location_rows, key=lambda row: (row.year, row.month))[-1]
        items.append(
            {
                "object_type": "scrap_price",
                "location": location,
                "net_price": _scrap_price_str(latest.net_price),
                "market_price": _scrap_price_str(latest.market_price),
                "deduction_fee": _scrap_price_str(latest.deduction_fee),
                "month": month_key(latest.year, latest.month),
            }
        )

    ranked = sorted(items, key=lambda item: item["location"])[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}
