"""包装运输费 summary / comparison / drilldown / drivers。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.repositories.llm.packaging_transport_fee_analysis_repository import (
    PackagingTransportFeeRow,
)


def _fee_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


def _row_key(row: PackagingTransportFeeRow) -> str:
    return f"{row.vehicle_model}|{row.part_number}"


def build_packaging_transport_fee_summary(
    rows: list[PackagingTransportFeeRow],
) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "packaging_transport_fee",
            "row_count": 0,
            "part_count": 0,
            "years": [],
            "locations": [],
            "vehicle_models": [],
        }

    keys = {_row_key(row) for row in rows}
    years = sorted({row.year for row in rows})
    locations = sorted({row.location for row in rows})
    vehicle_models = sorted({row.vehicle_model for row in rows})

    return {
        "subject": "packaging_transport_fee",
        "row_count": len(rows),
        "part_count": len(keys),
        "years": years,
        "locations": locations,
        "vehicle_models": vehicle_models,
    }


def build_packaging_transport_fee_comparison(
    rows: list[PackagingTransportFeeRow],
    *,
    location: str | None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "comparison",
            "found": False,
            "message": "未找到包装运输费记录",
            "location": location,
            "items": [],
        }

    by_year: dict[int, dict[str, PackagingTransportFeeRow]] = defaultdict(dict)
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
                    "vehicle_model": item.vehicle_model,
                    "part_number": item.part_number,
                    "part_name": item.part_name,
                    "packaging_transport_total": _fee_str(
                        item.packaging_transport_total
                    ),
                    "year": only_year,
                }
                for item in sorted(
                    by_year[only_year].values(),
                    key=lambda row: (row.vehicle_model, row.part_number),
                )[:50]
            ],
        }

    base_year, compare_year = years[0], years[-1]
    base_parts = by_year[base_year]
    compare_parts = by_year[compare_year]
    all_keys = sorted(set(base_parts) | set(compare_parts))

    items: list[dict[str, Any]] = []
    increased = 0
    decreased = 0
    unchanged = 0
    for key in all_keys:
        base_row = base_parts.get(key)
        compare_row = compare_parts.get(key)
        ref = compare_row or base_row
        base_total = base_row.packaging_transport_total if base_row else None
        compare_total = compare_row.packaging_transport_total if compare_row else None
        change: Decimal | None = None
        change_rate: str | None = None
        if base_total is not None and compare_total is not None:
            change = compare_total - base_total
            if base_total != 0:
                rate = (change / base_total).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
                change_rate = str(rate)
            if change > 0:
                increased += 1
            elif change < 0:
                decreased += 1
            else:
                unchanged += 1
        items.append(
            {
                "vehicle_model": ref.vehicle_model if ref else key.split("|", 1)[0],
                "part_number": ref.part_number if ref else key.split("|", 1)[-1],
                "part_name": ref.part_name if ref else None,
                "base_year": base_year,
                "compare_year": compare_year,
                "base_total": _fee_str(base_total),
                "compare_total": _fee_str(compare_total),
                "change": _fee_str(change) if change is not None else None,
                "change_rate": change_rate,
                "status": (
                    "new"
                    if base_total is None
                    else "removed"
                    if compare_total is None
                    else "changed"
                    if change not in (None, Decimal("0"))
                    else "unchanged"
                ),
            }
        )

    return {
        "kind": "comparison",
        "found": True,
        "dimensions": ["year", "vehicle_model", "part_number"],
        "location": location or rows[0].location,
        "years": [base_year, compare_year],
        "base_year": base_year,
        "compare_year": compare_year,
        "part_count": len(items),
        "increased_count": increased,
        "decreased_count": decreased,
        "unchanged_count": unchanged,
        "new_count": sum(1 for item in items if item["status"] == "new"),
        "removed_count": sum(1 for item in items if item["status"] == "removed"),
        "items": items[:100],
    }


def build_packaging_transport_fee_drilldown(
    rows: list[PackagingTransportFeeRow],
    *,
    part_token: str,
    head: PackagingTransportFeeRow | None = None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的包装运输费记录",
            "query_token": part_token,
            "items": [],
        }

    best = head or rows[0]
    items = [
        {
            "year": row.year,
            "location": row.location,
            "vehicle_model": row.vehicle_model,
            "part_number": row.part_number,
            "part_name": row.part_name,
            "unit_packaging_fee": _fee_str(row.unit_packaging_fee),
            "unit_transport_fee": _fee_str(row.unit_transport_fee),
            "packaging_transport_total": _fee_str(row.packaging_transport_total),
            "audit_status": row.audit_status,
        }
        for row in rows
    ]
    return {
        "kind": "drilldown",
        "found": True,
        "query_token": part_token,
        "part_number": best.part_number,
        "part_name": best.part_name,
        "vehicle_model": best.vehicle_model,
        "year": best.year,
        "location": best.location,
        "unit_packaging_fee": _fee_str(best.unit_packaging_fee),
        "unit_transport_fee": _fee_str(best.unit_transport_fee),
        "packaging_transport_total": _fee_str(best.packaging_transport_total),
        "audit_status": best.audit_status,
        "items": items,
    }


def build_packaging_transport_fee_drivers(
    rows: list[PackagingTransportFeeRow],
    *,
    top_n: int = 8,
) -> dict[str, Any]:
    if not rows:
        return {"kind": "drivers", "items": [], "top_n": top_n}

    latest_year = max(row.year for row in rows)
    latest_rows = [row for row in rows if row.year == latest_year]
    ranked = sorted(
        latest_rows, key=lambda row: row.packaging_transport_total, reverse=True
    )[:top_n]
    items = [
        {
            "rank": index,
            "object_type": "packaging_transport_fee",
            "year": row.year,
            "location": row.location,
            "vehicle_model": row.vehicle_model,
            "part_number": row.part_number,
            "part_name": row.part_name,
            "packaging_transport_total": _fee_str(row.packaging_transport_total),
        }
        for index, row in enumerate(ranked, start=1)
    ]
    return {"kind": "drivers", "items": items, "top_n": top_n}
