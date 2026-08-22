"""跨基地 / 跨序列对比。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.repositories.llm.cost_analysis_repository import L0MonthlyTotalRow
from app.schemas.llm.analysis_query import ComparisonBasis
from app.services.llm._money import money_str, month_key
from app.services.llm.query.comparison_basis import resolve_comparability


def build_location_comparison(
    rows: list[L0MonthlyTotalRow],
    *,
    basis: ComparisonBasis,
) -> dict[str, Any]:
    by_location: dict[str, list[L0MonthlyTotalRow]] = defaultdict(list)
    for row in rows:
        by_location[row.location].append(row)

    series: list[dict[str, Any]] = []
    for location, items in sorted(by_location.items()):
        ordered = sorted(items, key=lambda item: (item.year, item.month))
        points = [
            {
                "month": month_key(item.year, item.month),
                "grand_total_sum": money_str(item.grand_total_sum),
            }
            for item in ordered
        ]
        first = ordered[0].grand_total_sum
        last = ordered[-1].grand_total_sum
        change = last - first
        rate = (change / first).quantize(Decimal("0.0001")) if first != 0 else None
        series.append(
            {
                "location": location,
                "points": points,
                "start": money_str(first),
                "end": money_str(last),
                "change": money_str(change),
                "change_rate": str(rate) if rate is not None else None,
            }
        )

    winner: dict[str, str] | None = None
    best_rate: Decimal | None = None
    for item in series:
        rate_text = item.get("change_rate")
        if rate_text is None:
            continue
        rate = Decimal(rate_text)
        if best_rate is None:
            best_rate = rate
            winner = {"location": item["location"], "by": "change_rate"}
        elif rate > best_rate:
            best_rate = rate
            winner = {"location": item["location"], "by": "change_rate"}

    return {
        "kind": "comparison",
        "dimensions": ["location", "period"],
        "series": series,
        "winner": winner,
        "comparability": resolve_comparability(basis),
        "comparison_basis_label": basis.label,
    }
