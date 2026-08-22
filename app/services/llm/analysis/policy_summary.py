"""加减价政策 summary / drivers。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.repositories.llm.policy_analysis_repository import PolicyLadderRow
from app.services.llm._money import month_key


def build_policy_summary(rows: list[PolicyLadderRow]) -> dict[str, Any]:
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
        mills.add(row.steel_mill)
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
            {"month": month, "ladder_row_count": count}
            for month, count in sorted(by_month.items())
        ],
    }


def build_policy_drivers(rows: list[PolicyLadderRow], *, top_n: int = 15) -> dict[str, Any]:
    """按钢厂汇总非零加减价条数，辅助看「哪家政策多」。"""
    by_mill: dict[str, list[PolicyLadderRow]] = defaultdict(list)
    for row in rows:
        if row.price_adjustment == 0:
            continue
        by_mill[row.steel_mill].append(row)

    items: list[dict[str, Any]] = []
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

    ranked = sorted(items, key=lambda item: item["adjustment_row_count"], reverse=True)[
        :top_n
    ]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}
