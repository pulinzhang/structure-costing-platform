"""年度零件价 summary / comparison / drilldown / drivers。"""

from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.repositories.llm.annual_part_price_analysis_repository import AnnualPartPriceRow


def _unit_price_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


def build_annual_part_price_summary(
    rows: list[AnnualPartPriceRow],
) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "annual_part_price",
            "row_count": 0,
            "part_count": 0,
            "years": [],
            "locations": [],
            "supply_types": [],
        }

    part_numbers = {row.part_number for row in rows}
    years = sorted({row.year for row in rows})
    locations = sorted({row.location for row in rows})
    supply_types = sorted({row.supply_type for row in rows})

    return {
        "subject": "annual_part_price",
        "row_count": len(rows),
        "part_count": len(part_numbers),
        "years": years,
        "locations": locations,
        "supply_types": supply_types,
    }


def build_annual_part_price_comparison(
    rows: list[AnnualPartPriceRow],
    *,
    location: str | None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "comparison",
            "found": False,
            "message": "未找到年度零件价记录",
            "location": location,
            "items": [],
        }

    by_year: dict[int, dict[str, AnnualPartPriceRow]] = defaultdict(dict)
    for row in rows:
        by_year[row.year][row.part_number] = row

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
                    "supply_type": item.supply_type,
                    "unit": item.unit,
                    "unit_price": _unit_price_str(item.unit_price),
                    "year": only_year,
                }
                for item in sorted(by_year[only_year].values(), key=lambda row: row.part_number)[
                    :50
                ]
            ],
        }

    base_year, compare_year = years[0], years[-1]
    base_parts = by_year[base_year]
    compare_parts = by_year[compare_year]
    all_numbers = sorted(set(base_parts) | set(compare_parts))

    items: list[dict[str, Any]] = []
    increased = 0
    decreased = 0
    unchanged = 0
    for part_number in all_numbers:
        base_row = base_parts.get(part_number)
        compare_row = compare_parts.get(part_number)
        base_price = base_row.unit_price if base_row else None
        compare_price = compare_row.unit_price if compare_row else None
        ref = compare_row or base_row
        change: Decimal | None = None
        change_rate: str | None = None
        if base_price is not None and compare_price is not None:
            change = compare_price - base_price
            if base_price != 0:
                rate = (change / base_price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                change_rate = str(rate)
            if change > 0:
                increased += 1
            elif change < 0:
                decreased += 1
            else:
                unchanged += 1
        items.append(
            {
                "part_number": part_number,
                "part_name": ref.part_name if ref else None,
                "supply_type": ref.supply_type if ref else None,
                "unit": ref.unit if ref else "",
                "base_year": base_year,
                "compare_year": compare_year,
                "base_unit_price": _unit_price_str(base_price),
                "compare_unit_price": _unit_price_str(compare_price),
                "change": _unit_price_str(change) if change is not None else None,
                "change_rate": change_rate,
                "status": (
                    "new"
                    if base_price is None
                    else "removed"
                    if compare_price is None
                    else "changed"
                    if change not in (None, Decimal("0"))
                    else "unchanged"
                ),
            }
        )

    return {
        "kind": "comparison",
        "found": True,
        "dimensions": ["year", "part_number"],
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


def build_annual_part_price_drilldown(
    rows: list[AnnualPartPriceRow],
    *,
    part_token: str,
    head: AnnualPartPriceRow | None = None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的年度零件价记录",
            "query_token": part_token,
            "items": [],
        }

    best = head or rows[0]
    items = [
        {
            "year": row.year,
            "location": row.location,
            "part_number": row.part_number,
            "part_name": row.part_name,
            "supply_type": row.supply_type,
            "unit": row.unit,
            "unit_price": _unit_price_str(row.unit_price),
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
        "year": best.year,
        "location": best.location,
        "supply_type": best.supply_type,
        "unit": best.unit,
        "unit_price": _unit_price_str(best.unit_price),
        "audit_status": best.audit_status,
        "items": items,
    }


def build_annual_part_price_drivers(
    rows: list[AnnualPartPriceRow],
    *,
    top_n: int = 8,
) -> dict[str, Any]:
    if not rows:
        return {"kind": "drivers", "items": [], "top_n": top_n}

    latest_year = max(row.year for row in rows)
    latest_rows = [row for row in rows if row.year == latest_year]
    ranked = sorted(latest_rows, key=lambda row: row.unit_price, reverse=True)[:top_n]
    items = [
        {
            "rank": index,
            "object_type": "annual_part_price",
            "year": row.year,
            "location": row.location,
            "part_number": row.part_number,
            "part_name": row.part_name,
            "supply_type": row.supply_type,
            "unit_price": _unit_price_str(row.unit_price),
        }
        for index, row in enumerate(ranked, start=1)
    ]
    return {"kind": "drivers", "items": items, "top_n": top_n}
