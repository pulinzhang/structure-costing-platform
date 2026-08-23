"""单号钻取（含区间差分 period_diff）。"""

from __future__ import annotations

from typing import Any

from app.common.part_number import part_numbers_match
from app.repositories.llm.cost_analysis_repository import L0PartPeriodRow
from app.services.llm._money import money_str, month_key
from app.services.llm.analysis._formulas import build_period_diff


def build_drilldown(
    rows: list[L0PartPeriodRow],
    *,
    part_number: str,
) -> dict[str, Any]:
    matched = [row for row in rows if part_numbers_match(row.part_number, part_number)]
    if not matched:
        return {
            "kind": "drilldown",
            "part_number": part_number,
            "message": "未找到该零件号的 L0 核价结果",
            "points": [],
            "period_diff": None,
        }

    ordered = sorted(matched, key=lambda item: (item.year, item.month))
    latest = ordered[-1]
    start_row = ordered[0]
    end_row = ordered[-1]
    points = [
        {
            "month": month_key(row.year, row.month),
            "grand_total": money_str(row.grand_total),
            "total_amount": money_str(row.total_amount),
            "calc_status": row.calc_status,
            "bom_version": row.bom_version,
        }
        for row in ordered
    ]
    period_diff = None
    if len(ordered) >= 1:
        period_diff = build_period_diff(start_row, end_row)

    return {
        "kind": "drilldown",
        "part_number": latest.part_number,
        "part_name": latest.part_name,
        "latest": {
            "month": month_key(latest.year, latest.month),
            "grand_total": money_str(latest.grand_total),
            "total_amount": money_str(latest.total_amount),
            "stamping_amount": money_str(latest.stamping_amount),
            "purchased_amount": money_str(latest.purchased_amount),
            "bundle_amount": money_str(latest.bundle_amount),
            "welding_amount": money_str(latest.welding_amount),
            "welding_other_fee": money_str(latest.welding_other_fee),
            "indirect_amount": money_str(latest.indirect_amount),
            "calc_status": latest.calc_status,
            "calc_message": latest.calc_message,
            "missing_leaf_count": latest.missing_leaf_count,
            "bom_version": latest.bom_version,
        },
        "period_diff": period_diff,
        "points": points,
    }
