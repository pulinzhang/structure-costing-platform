"""风险 / 缺价 / partial。"""

from __future__ import annotations

from typing import Any

from app.repositories.llm.cost_analysis_repository import L0PartPeriodRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow


def build_risks(rows: list[L0PartPeriodRow], *, sample_limit: int = 20) -> dict[str, Any]:
    partial_rows = [row for row in rows if row.calc_status != "ok"]
    by_part: dict[str, L0PartPeriodRow] = {}
    for row in partial_rows:
        by_part[row.part_number] = row

    samples = []
    reason_counts: dict[str, int] = {}
    for row in list(by_part.values())[:sample_limit]:
        samples.append(
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "calc_status": row.calc_status,
                "missing_leaf_count": row.missing_leaf_count,
                "calc_message": row.calc_message,
            }
        )
        key = (row.calc_message or row.calc_status or "unknown").strip()[:80]
        reason_counts[key] = reason_counts.get(key, 0) + 1

    risks = []
    if by_part:
        risks.append(
            {
                "risk_type": "missing_price",
                "severity": "high" if len(by_part) >= 5 else "medium",
                "count": len(by_part),
                "sample_part_numbers": [item["part_number"] for item in samples],
                "message": "存在 partial / 缺价零部件，影响核价完备性",
                "reason_counts": reason_counts,
                "samples": samples,
            }
        )

    return {
        "kind": "risk",
        "partial_count": len(by_part),
        "risks": risks,
    }


def build_stamping_risks(
    rows: list[StampingPartPeriodRow],
    *,
    sample_limit: int = 20,
) -> dict[str, Any]:
    bad_rows = [row for row in rows if row.calc_status != "success"]
    by_part: dict[str, StampingPartPeriodRow] = {}
    for row in bad_rows:
        by_part[row.part_number] = row

    samples = []
    status_counts: dict[str, int] = {}
    for row in list(by_part.values())[:sample_limit]:
        samples.append(
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "calc_status": row.calc_status,
                "stamping_supplier": row.stamping_supplier,
            }
        )
        status_counts[row.calc_status] = status_counts.get(row.calc_status, 0) + 1

    risks = []
    if by_part:
        risks.append(
            {
                "risk_type": "stamping_calc_failed",
                "severity": "high" if len(by_part) >= 5 else "medium",
                "count": len(by_part),
                "sample_part_numbers": [item["part_number"] for item in samples],
                "message": "冲压零件价格存在非 success 记录",
                "status_counts": status_counts,
                "samples": samples,
            }
        )

    return {
        "kind": "risk",
        "partial_count": len(by_part),
        "risks": risks,
    }
