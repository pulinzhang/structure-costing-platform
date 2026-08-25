"""风险 / 缺价 / partial（B.6.1 risk.缺价）。"""

from __future__ import annotations

from typing import Any

from app.repositories.llm.cost_analysis_repository import L0PartPeriodRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow


def build_risks(
    rows: list[L0PartPeriodRow],
    *,
    sample_limit: int = 20,
    filtered_missing_price_count: int = 0,
) -> dict[str, Any]:
    missing_by_part: dict[str, L0PartPeriodRow] = {}
    for row in rows:
        if row.grand_total is None or row.grand_total == 0:
            missing_by_part[row.part_number] = row

    partial_rows = [row for row in rows if row.calc_status != "ok"]
    partial_by_part: dict[str, L0PartPeriodRow] = {}
    for row in partial_rows:
        partial_by_part[row.part_number] = row

    missing_samples = []
    for row in list(missing_by_part.values())[:sample_limit]:
        missing_samples.append(
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "month": f"{row.year:04d}-{row.month:02d}",
                "grand_total": str(row.grand_total),
            }
        )

    partial_samples = []
    reason_counts: dict[str, int] = {}
    for row in list(partial_by_part.values())[:sample_limit]:
        partial_samples.append(
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

    risks: list[dict[str, Any]] = []
    if missing_by_part:
        risks.append(
            {
                "risk_type": "missing_price",
                "severity": "high" if len(missing_by_part) >= 5 else "medium",
                "count": len(missing_by_part),
                "missing_price_items": missing_samples,
                "sample_part_numbers": [item["part_number"] for item in missing_samples],
                "message": "存在缺价记录（price=0 或空），已按零件号去重",
            }
        )
    if partial_by_part:
        risks.append(
            {
                "risk_type": "calc_partial",
                "severity": "high" if len(partial_by_part) >= 5 else "medium",
                "count": len(partial_by_part),
                "sample_part_numbers": [item["part_number"] for item in partial_samples],
                "message": "存在 partial / 缺价零部件，影响核价完备性",
                "reason_counts": reason_counts,
                "samples": partial_samples,
            }
        )

    return {
        "kind": "risk",
        "partial_count": len(partial_by_part),
        "missing_price_count": len(missing_by_part),
        "filtered_missing_price_count": filtered_missing_price_count,
        "risks": risks,
    }


def build_stamping_risks(
    rows: list[StampingPartPeriodRow],
    *,
    sample_limit: int = 20,
) -> dict[str, Any]:
    missing_by_part: dict[str, StampingPartPeriodRow] = {}
    for row in rows:
        if row.unit_cost is None or row.unit_cost == 0:
            missing_by_part[row.part_number] = row

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

    risks: list[dict[str, Any]] = []
    if missing_by_part:
        risks.append(
            {
                "risk_type": "missing_price",
                "severity": "high" if len(missing_by_part) >= 5 else "medium",
                "count": len(missing_by_part),
                "message": "冲压零件存在缺价记录（unit_cost=0 或空）",
            }
        )
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
        "missing_price_count": len(missing_by_part),
        "risks": risks,
    }
