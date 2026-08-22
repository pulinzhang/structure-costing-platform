"""趋势分析：环比 / 累计涨幅 / 异常月（业务分析，不在 Repository）。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.repositories.llm.cost_analysis_repository import L0MonthlyTotalRow
from app.repositories.llm.steel_price_analysis_repository import SteelMonthlyAvgRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
from app.schemas.llm.analysis_query import ComparisonBasis
from app.services.llm._money import money_str, month_key
from app.services.llm.query.comparison_basis import resolve_comparability


def build_cost_trend(
    rows: list[L0MonthlyTotalRow],
    *,
    basis: ComparisonBasis,
) -> dict[str, Any]:
    # 单基地序列：按月合并（同月多基地则分 location 由 comparison 处理）
    by_month: dict[str, Decimal] = {}
    for row in rows:
        key = month_key(row.year, row.month)
        by_month[key] = by_month.get(key, Decimal("0")) + row.grand_total_sum

    return _trend_from_series(
        sorted(by_month.items(), key=lambda item: item[0]),
        value_label="grand_total_sum",
        basis=basis,
    )


def build_steel_trend(
    rows: list[SteelMonthlyAvgRow],
    *,
    basis: ComparisonBasis,
) -> dict[str, Any]:
    series = [
        (month_key(row.year, row.month), row.avg_final_price)
        for row in sorted(rows, key=lambda item: (item.year, item.month))
    ]
    return _trend_from_series(series, value_label="avg_final_price", basis=basis)


def build_stamping_trend(
    rows: list[StampingPartPeriodRow],
    *,
    basis: ComparisonBasis,
) -> dict[str, Any]:
    """按月汇总冲压件 unit_cost 合计，用于环比。"""
    by_month: dict[str, Decimal] = {}
    for row in rows:
        key = month_key(row.year, row.month)
        by_month[key] = by_month.get(key, Decimal("0")) + row.unit_cost
    return _trend_from_series(
        sorted(by_month.items(), key=lambda item: item[0]),
        value_label="unit_cost_sum",
        basis=basis,
    )


def _trend_from_series(
    series: list[tuple[str, Decimal]],
    *,
    value_label: str,
    basis: ComparisonBasis,
) -> dict[str, Any]:
    if not series:
        return {
            "kind": "trend",
            "points": [],
            "comparability": resolve_comparability(basis),
            "comparison_basis_label": basis.label,
        }

    points: list[dict[str, Any]] = []
    prev: Decimal | None = None
    for month, value in series:
        mom_delta = None
        mom_rate = None
        if prev is not None:
            mom_delta = value - prev
            if prev != 0:
                mom_rate = (mom_delta / prev).quantize(Decimal("0.0001"))
        points.append(
            {
                "month": month,
                value_label: money_str(value),
                "mom_delta": money_str(mom_delta) if mom_delta is not None else None,
                "mom_rate": str(mom_rate) if mom_rate is not None else None,
            }
        )
        prev = value

    values = [item[1] for item in series]
    first = values[0]
    last = values[-1]
    cumulative_delta = last - first
    cumulative_rate = (
        (cumulative_delta / first).quantize(Decimal("0.0001")) if first != 0 else None
    )

    # 简单异常：|环比| > 10%
    anomalies: list[str] = []
    for point in points:
        rate = point.get("mom_rate")
        if rate is None:
            continue
        if abs(Decimal(rate)) >= Decimal("0.10"):
            anomalies.append(str(point["month"]))

    return {
        "kind": "trend",
        "points": points,
        "min": money_str(min(values)),
        "max": money_str(max(values)),
        "avg": money_str(sum(values) / Decimal(len(values))),
        "start": money_str(first),
        "end": money_str(last),
        "cumulative_delta": money_str(cumulative_delta),
        "cumulative_rate": str(cumulative_rate) if cumulative_rate is not None else None,
        "anomaly_months": anomalies,
        "comparability": resolve_comparability(basis),
        "comparison_basis_label": basis.label,
        "notes": basis.notes,
    }
