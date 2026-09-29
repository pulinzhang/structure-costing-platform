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
    """按 steel_mill_id 汇总非零加减价条数。钢厂字用结果行上的字。"""
    by_mill: dict[int, list[PolicyLadderRow]] = defaultdict(list)
    for row in rows:
        if row.price_adjustment == 0:
            continue
        by_mill[row.steel_mill_id].append(row)

    items: list[DriverItem] = []
    for _mill_id, mill_rows in by_mill.items():
        adjustments = [row.price_adjustment for row in mill_rows]
        items.append(
            {
                "object_type": "steel_price_policy",
                "steel_mill": mill_rows[0].steel_mill,
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


def _policy_jump_hint(prev_row: PolicyLadderRow, curr_row: PolicyLadderRow) -> str:
    """表页没变才提示传错；表页换了就点名两张表。"""
    prev_sheet = prev_row.sheet_name
    curr_sheet = curr_row.sheet_name
    if prev_sheet == curr_sheet:
        return f"表页仍是「{curr_sheet}」。请在加减价政策列表按这张表页核对，看是不是传错月或错档。"
    return (
        f"上月表页「{prev_sheet}」，本月表页「{curr_sheet}」，钢厂都是「{curr_row.steel_mill}」。"
        "表页换了，这两档不是同一张表上的同一格，不要当成传错月或错档。"
        "请分别打开这两个月的表页核对。"
    )


def build_policy_mom_anomalies(
    rows: list[PolicyLadderRow],
    *,
    top_n: int = 15,
    min_abs_change: int = 30,
) -> DomainAnomaliesPayload:
    """同阶梯按 steel_mill_id 环比。清单按月份从早到晚。钢厂字用结果行上的字。"""
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
                    "prev_sheet_name": prev_row.sheet_name,
                    "sheet_name": curr_row.sheet_name,
                    "hint": _policy_jump_hint(prev_row, curr_row),
                }
            )

    picked = sorted(
        spikes,
        key=lambda item: (
            abs(int(item.get("change") or 0)),
            abs(Decimal(str(item.get("change_rate") or "0"))),
        ),
        reverse=True,
    )[:top_n]
    picked.sort(key=lambda item: str(item.get("month") or ""))
    for index, item in enumerate(picked, start=1):
        item["rank"] = index
    return {
        "kind": "policy_anomalies",
        "items": picked,
        "top_n": top_n,
        "subject": "steel_price_policy",
    }
