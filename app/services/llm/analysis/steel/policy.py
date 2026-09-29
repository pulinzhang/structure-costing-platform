"""加减价政策 summary / trend / 月度异常。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.repositories.llm.policy_analysis_repository import PolicyLadderRow
from app.schemas.llm.analysis_payload import (
    DomainAnomaliesPayload,
    DriverItem,
    DriversPayload,
    MomAnomalyItem,
    SummaryPayload,
    TrendPayload,
)
from app.schemas.llm.analysis_query import ComparisonBasis
from app.services.llm._money import month_key
from app.services.llm.analysis.shared.cost_trend import trend_from_series


def build_policy_summary(rows: list[PolicyLadderRow]) -> SummaryPayload:
    if not rows:
        return {
            "subject": "steel_price_policy",
            "policy_count": 0,
            "ladder_row_count": 0,
            "steel_mill_count": 0,
            "category_count": 0,
            "thickness_policy_count": 0,
            "width_policy_count": 0,
            "non_zero_adjustment_count": 0,
            "months": [],
        }

    policy_ids: set[int] = set()
    mills: set[str] = set()
    categories: set[str] = set()
    thickness_policies: set[int] = set()
    width_policies: set[int] = set()
    non_zero = 0
    by_month: dict[str, int] = defaultdict(int)

    for row in rows:
        policy_ids.add(row.policy_id)
        mills.add(str(row.steel_mill_id))
        categories.add(row.category_name)
        if row.policy_type == "THICKNESS":
            thickness_policies.add(row.policy_id)
        elif row.policy_type == "WIDTH":
            width_policies.add(row.policy_id)
        if row.price_adjustment != 0:
            non_zero += 1
        by_month[month_key(row.year, row.month)] += 1

    return {
        "subject": "steel_price_policy",
        "policy_count": len(policy_ids),
        "ladder_row_count": len(rows),
        "steel_mill_count": len(mills),
        "category_count": len(categories),
        "thickness_policy_count": len(thickness_policies),
        "width_policy_count": len(width_policies),
        "non_zero_adjustment_count": non_zero,
        "months": [
            {"month": month, "ladder_row_count": count} for month, count in sorted(by_month.items())
        ],
    }


def build_policy_drivers(rows: list[PolicyLadderRow], *, top_n: int = 15) -> DriversPayload:
    """按钢厂汇总非零加减价条数，辅助看「哪家政策多」。"""
    by_mill: dict[str, list[PolicyLadderRow]] = defaultdict(list)
    for row in rows:
        if row.price_adjustment == 0:
            continue
        by_mill[row.steel_mill].append(row)

    items: list[DriverItem] = []
    for mill, mill_rows in by_mill.items():
        adjustments = [row.price_adjustment for row in mill_rows]
        items.append(
            {
                "object_type": "steel_price_policy",
                "steel_mill": mill,
                "adjustment_row_count": len(mill_rows),
                "max_adjustment": max(adjustments),
                "min_adjustment": min(adjustments),
            }
        )

    ranked = sorted(items, key=lambda item: int(str(item["adjustment_row_count"])), reverse=True)[
        :top_n
    ]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}


def build_policy_trend(
    rows: list[PolicyLadderRow],
    *,
    basis: ComparisonBasis,
) -> TrendPayload:
    """各月加减价阶梯「非零条数」序列（看政策量是否突变）。"""
    by_month: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.price_adjustment != 0:
            by_month[month_key(row.year, row.month)] += 1

    series = [(month, Decimal(count)) for month, count in sorted(by_month.items())]
    trend = trend_from_series(series, value_label="non_zero_ladder_count", basis=basis)
    trend["subject"] = "steel_price_policy"
    return trend


def _policy_ladder_key(row: PolicyLadderRow) -> str:
    return "|".join(
        [
            str(row.steel_mill_id),
            row.category_name,
            row.policy_type,
            row.grade_value or "",
            str(row.thick_min or ""),
            str(row.thick_max or ""),
            str(row.is_base),
        ]
    )


def _format_thickness_band(row: PolicyLadderRow) -> str:
    if row.thick_min is None and row.thick_max is None:
        return "-"
    if row.thick_min is not None and row.thick_max is not None:
        return f"{row.thick_min}~{row.thick_max}"
    if row.thick_min is not None:
        return f">={row.thick_min}"
    return f"<={row.thick_max}"


def build_policy_mom_anomalies(
    rows: list[PolicyLadderRow],
    *,
    top_n: int = 15,
    min_abs_change: int = 30,
) -> DomainAnomaliesPayload:
    """同阶梯在各月间的加减价跳变（疑似传错政策/月份）。"""
    by_key: dict[str, dict[str, PolicyLadderRow]] = defaultdict(dict)
    for row in rows:
        month = month_key(row.year, row.month)
        key = _policy_ladder_key(row)
        by_key[key][month] = row

    spikes: list[MomAnomalyItem] = []
    for _key, month_map in by_key.items():
        ordered_months = sorted(month_map.keys())
        ordered_rows = [month_map[month] for month in ordered_months]
        for index in range(1, len(ordered_rows)):
            prev_row = ordered_rows[index - 1]
            curr_row = ordered_rows[index]
            change = curr_row.price_adjustment - prev_row.price_adjustment
            if abs(change) < min_abs_change:
                continue
            rate: Decimal | None = None
            if prev_row.price_adjustment != 0:
                rate = (Decimal(change) / Decimal(prev_row.price_adjustment)).quantize(
                    Decimal("0.0001")
                )
            spikes.append(
                {
                    "anomaly_type": "policy_adjustment_jump",
                    "steel_mill": curr_row.steel_mill,
                    "category_name": curr_row.category_name,
                    "policy_type": curr_row.policy_type,
                    "grade_value": curr_row.grade_value,
                    "thickness_band": _format_thickness_band(curr_row),
                    "month": month_key(curr_row.year, curr_row.month),
                    "prev_month": month_key(prev_row.year, prev_row.month),
                    "prev_adjustment": prev_row.price_adjustment,
                    "curr_adjustment": curr_row.price_adjustment,
                    "change": change,
                    "change_rate": str(rate) if rate is not None else None,
                    "hint": "加减价环比跳变较大，建议核对是否上传错月或错档",
                }
            )

    ranked = sorted(
        spikes,
        key=lambda item: (
            abs(int(item.get("change") or 0)),
            abs(Decimal(str(item.get("change_rate") or "0"))),
        ),
        reverse=True,
    )[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {
        "kind": "policy_anomalies",
        "items": ranked,
        "top_n": top_n,
        "subject": "steel_price_policy",
    }
