"""成品焊接费 summary / comparison / drilldown / drivers。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.repositories.llm.l0_welding_fee_analysis_repository import L0WeldingFeeRow


def _fee_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


def _row_key(row: L0WeldingFeeRow) -> str:
    return f"{row.vehicle_model}|{row.bom_version}|{row.part_number}"


def build_l0_welding_fee_summary(rows: list[L0WeldingFeeRow]) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "l0_welding_fee",
            "row_count": 0,
            "part_count": 0,
            "years": [],
            "locations": [],
            "vehicle_models": [],
        }

    return {
        "subject": "l0_welding_fee",
        "row_count": len(rows),
        "part_count": len({_row_key(row) for row in rows}),
        "years": sorted({row.year for row in rows}),
        "locations": sorted({row.location for row in rows}),
        "vehicle_models": sorted({row.vehicle_model for row in rows}),
    }


def build_l0_welding_fee_comparison(
    rows: list[L0WeldingFeeRow],
    *,
    location: str | None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "comparison",
            "found": False,
            "message": "未找到成品焊接费记录",
            "location": location,
            "items": [],
        }

    by_year: dict[int, dict[str, L0WeldingFeeRow]] = defaultdict(dict)
    for row in rows:
        by_year[row.year][_row_key(row)] = row

    years = sorted(by_year.keys())
    if len(years) < 2:
        only_year = years[0]
        return {
            "kind": "comparison",
            "found": False,
            "message": f"仅命中 {only_year} 年数据，暂无法做跨年度对比",
            "location": location or rows[0].location,
            "years": years,
            "part_count": len(by_year[only_year]),
            "items": [
                {
                    "part_number": item.part_number,
                    "part_name": item.part_name,
                    "vehicle_model": item.vehicle_model,
                    "bom_version": item.bom_version,
                    "final_l0_welding_fee": _fee_str(item.final_l0_welding_fee),
                    "year": only_year,
                }
                for item in sorted(
                    by_year[only_year].values(),
                    key=lambda row: row.part_number,
                )[:50]
            ],
        }

    base_year, compare_year = years[0], years[-1]
    base_parts = by_year[base_year]
    compare_parts = by_year[compare_year]
    all_keys = sorted(set(base_parts) | set(compare_parts))

    items: list[dict[str, Any]] = []
    for key in all_keys:
        base_row = base_parts.get(key)
        compare_row = compare_parts.get(key)
        ref = compare_row or base_row
        base_fee = (
            base_row.final_l0_welding_fee or base_row.total_l0_welding_fee if base_row else None
        )
        compare_fee = (
            compare_row.final_l0_welding_fee or compare_row.total_l0_welding_fee
            if compare_row
            else None
        )
        change: Decimal | None = None
        change_rate: str | None = None
        if base_fee is not None and compare_fee is not None:
            change = compare_fee - base_fee
            if base_fee != 0:
                rate = (change / base_fee).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                change_rate = str(rate)
        items.append(
            {
                "part_number": ref.part_number if ref else key.split("|")[-1],
                "part_name": ref.part_name if ref else None,
                "vehicle_model": ref.vehicle_model if ref else None,
                "bom_version": ref.bom_version if ref else None,
                "base_year": base_year,
                "compare_year": compare_year,
                "base_fee": _fee_str(base_fee),
                "compare_fee": _fee_str(compare_fee),
                "change": _fee_str(change) if change is not None else None,
                "change_rate": change_rate,
            }
        )

    return {
        "kind": "comparison",
        "found": True,
        "dimensions": ["year", "part_number"],
        "location": location or rows[0].location,
        "years": [base_year, compare_year],
        "part_count": len(items),
        "items": items[:100],
    }


def build_l0_welding_fee_drilldown(
    rows: list[L0WeldingFeeRow],
    *,
    part_token: str,
    head: L0WeldingFeeRow | None = None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的成品焊接费记录",
            "query_token": part_token,
            "items": [],
        }

    best = head or rows[0]
    return {
        "kind": "drilldown",
        "found": True,
        "query_token": part_token,
        "part_number": best.part_number,
        "part_name": best.part_name,
        "year": best.year,
        "location": best.location,
        "vehicle_model": best.vehicle_model,
        "bom_version": best.bom_version,
        "total_l0_welding_fee": _fee_str(best.total_l0_welding_fee),
        "final_l0_welding_fee": _fee_str(best.final_l0_welding_fee),
        "calc_status": best.calc_status,
        "audit_status": best.audit_status,
        "items": [
            {
                "year": row.year,
                "part_number": row.part_number,
                "final_l0_welding_fee": _fee_str(
                    row.final_l0_welding_fee or row.total_l0_welding_fee
                ),
                "calc_status": row.calc_status,
            }
            for row in rows
        ],
    }


def build_l0_welding_fee_drivers(
    rows: list[L0WeldingFeeRow],
    *,
    top_n: int = 8,
) -> dict[str, Any]:
    if not rows:
        return {"kind": "drivers", "items": [], "top_n": top_n}

    latest_year = max(row.year for row in rows)
    latest_rows = [row for row in rows if row.year == latest_year]
    ranked = sorted(
        latest_rows,
        key=lambda row: row.final_l0_welding_fee or row.total_l0_welding_fee,
        reverse=True,
    )[:top_n]
    items = [
        {
            "rank": index,
            "object_type": "l0_welding_fee",
            "year": row.year,
            "part_number": row.part_number,
            "part_name": row.part_name,
            "final_l0_welding_fee": _fee_str(row.final_l0_welding_fee or row.total_l0_welding_fee),
        }
        for index, row in enumerate(ranked, start=1)
    ]
    return {"kind": "drivers", "items": items, "top_n": top_n}
