"""跨基地 / 跨序列对比（B.6.1 spread）。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.repositories.llm.cost_analysis_repository import L0MonthlyTotalRow
from app.schemas.llm.analysis_query import ComparisonBasis
from app.services.llm._money import money_str, month_key, rate_str
from app.services.llm.analysis.shared.formulas import compute_change_rate, compute_spread
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
        rate = compute_change_rate(first, last)
        series.append(
            {
                "location": location,
                "points": points,
                "start": money_str(first),
                "end": money_str(last),
                "change": money_str(change),
                "change_rate": rate_str(rate) if rate is not None else None,
                "status": "valid" if rate is not None else "invalid",
            }
        )

    winner: dict[str, str] | None = None
    best_rate: Decimal | None = None
    for item in series:
        rate_text = item.get("change_rate")
        if rate_text is None:
            continue
        rate = Decimal(rate_text)
        if best_rate is None or rate > best_rate:
            best_rate = rate
            winner = {"location": item["location"], "by": "change_rate"}

    spreads: list[dict[str, Any]] = []
    for left_index in range(len(series)):
        for right_index in range(left_index + 1, len(series)):
            left = series[left_index]
            right = series[right_index]
            left_rate = (
                Decimal(str(left["change_rate"])) if left.get("change_rate") is not None else None
            )
            right_rate = (
                Decimal(str(right["change_rate"])) if right.get("change_rate") is not None else None
            )
            spread_result = compute_spread(left_rate, right_rate)
            spreads.append(
                {
                    "location_a": left["location"],
                    "location_b": right["location"],
                    **spread_result,
                }
            )

    return {
        "kind": "comparison",
        "dimensions": ["location", "period"],
        "series": series,
        "spreads": spreads,
        "winner": winner,
        "comparability": resolve_comparability(basis),
        "comparison_basis_label": basis.label,
    }
