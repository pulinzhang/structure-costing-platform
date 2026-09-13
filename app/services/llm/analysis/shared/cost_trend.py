"""趋势分析：环比 / 累计涨幅 / 异常月（业务分析，不在 Repository）。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.repositories.llm.cost_analysis import L0MonthlyTotalRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
from app.repositories.llm.steel_price_analysis_repository import SteelMonthlyAvgRow
from app.schemas.llm.analysis_query import ComparisonBasis
from app.services.llm._money import money_str, month_key, rate_str
from app.services.llm.analysis.shared.formulas import (
    compute_cumulative_rate,
    compute_mom_rate,
    detect_anomaly_months,
)
from app.services.llm.comparison_basis import resolve_comparability


def build_cost_trend(
    rows: list[L0MonthlyTotalRow],
    *,
    basis: ComparisonBasis,
    single_month: bool = False,
) -> dict[str, Any]:
    by_month: dict[str, Decimal] = {}
    for row in rows:
        key = month_key(row.year, row.month)
        by_month[key] = by_month.get(key, Decimal("0")) + row.grand_total_sum

    return trend_from_series(
        sorted(by_month.items(), key=lambda item: item[0]),
        value_label="grand_total_sum",
        basis=basis,
        single_month=single_month,
    )


def build_steel_trend(
    rows: list[SteelMonthlyAvgRow],
    *,
    basis: ComparisonBasis,
    single_month: bool = False,
) -> dict[str, Any]:
    series = [
        (month_key(row.year, row.month), row.avg_final_price)
        for row in sorted(rows, key=lambda item: (item.year, item.month))
    ]
    return trend_from_series(
        series,
        value_label="avg_final_price",
        basis=basis,
        single_month=single_month,
    )


def build_stamping_trend(
    rows: list[StampingPartPeriodRow],
    *,
    basis: ComparisonBasis,
    single_month: bool = False,
) -> dict[str, Any]:
    by_month: dict[str, Decimal] = {}
    for row in rows:
        key = month_key(row.year, row.month)
        by_month[key] = by_month.get(key, Decimal("0")) + row.unit_cost
    return trend_from_series(
        sorted(by_month.items(), key=lambda item: item[0]),
        value_label="unit_cost_sum",
        basis=basis,
        single_month=single_month,
    )


def trend_from_series(
    series: list[tuple[str, Decimal]],
    *,
    value_label: str,
    basis: ComparisonBasis,
    single_month: bool = False,
) -> dict[str, Any]:
    if not series:
        return {
            "kind": "trend",
            "points": [],
            "comparability": resolve_comparability(basis),
            "comparison_basis_label": basis.label,
            "anomaly_months": [],
            "anomaly_note": None,
        }

    points: list[dict[str, Any]] = []
    prev: Decimal | None = None
    for month, value in series:
        mom_delta = None
        mom_rate = None
        if prev is not None:
            mom_delta = value - prev
            mom_rate = compute_mom_rate(prev, value)
        points.append(
            {
                "month": month,
                value_label: money_str(value),
                "mom_delta": money_str(mom_delta) if mom_delta is not None else None,
                "mom_rate": rate_str(mom_rate) if mom_rate is not None else None,
            }
        )
        prev = value

    values = [item[1] for item in series]
    first = values[0]
    last = values[-1]
    cumulative_delta = last - first
    is_single = single_month or len(series) <= 1
    cumulative_rate = compute_cumulative_rate(first, last, single_month=is_single)
    anomaly_months, anomaly_note = detect_anomaly_months(points)

    return {
        "kind": "trend",
        "points": points,
        "min": money_str(min(values)),
        "max": money_str(max(values)),
        "avg": money_str(sum(values) / Decimal(len(values))),
        "start": money_str(first),
        "end": money_str(last),
        "cumulative_delta": money_str(cumulative_delta),
        "cumulative_rate": rate_str(cumulative_rate) if cumulative_rate is not None else None,
        "anomaly_months": anomaly_months,
        "anomaly_note": anomaly_note,
        "comparability": resolve_comparability(basis),
        "comparison_basis_label": basis.label,
        "notes": basis.notes,
    }
