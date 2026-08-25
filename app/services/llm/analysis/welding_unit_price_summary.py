"""焊接单价 summary / comparison / drivers。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.repositories.llm.welding_unit_price_analysis_repository import WeldingUnitPriceRow


def _unit_price_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


def build_welding_unit_price_summary(rows: list[WeldingUnitPriceRow]) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "welding_unit_price",
            "row_count": 0,
            "item_count": 0,
            "years": [],
            "locations": [],
        }

    item_names = {row.item_name for row in rows}
    years = sorted({row.year for row in rows})
    locations = sorted({row.location for row in rows})

    return {
        "subject": "welding_unit_price",
        "row_count": len(rows),
        "item_count": len(item_names),
        "years": years,
        "locations": locations,
    }


def build_welding_unit_price_comparison(
    rows: list[WeldingUnitPriceRow],
    *,
    location: str | None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "comparison",
            "found": False,
            "message": "未找到焊接单价记录",
            "location": location,
            "items": [],
        }

    by_year: dict[int, dict[str, WeldingUnitPriceRow]] = defaultdict(dict)
    for row in rows:
        by_year[row.year][row.item_name] = row

    years = sorted(by_year.keys())
    if len(years) < 2:
        only_year = years[0]
        return {
            "kind": "comparison",
            "found": False,
            "message": f"仅命中 {only_year} 年数据，暂无法做跨年度对比",
            "location": location or rows[0].location,
            "years": years,
            "item_count": len(by_year[only_year]),
            "items": [
                {
                    "item_name": item.item_name,
                    "unit": item.unit,
                    "unit_price": _unit_price_str(item.unit_price),
                    "year": only_year,
                }
                for item in sorted(by_year[only_year].values(), key=lambda row: row.item_name)
            ],
        }

    base_year, compare_year = years[0], years[-1]
    base_items = by_year[base_year]
    compare_items = by_year[compare_year]
    all_names = sorted(set(base_items) | set(compare_items))

    items: list[dict[str, Any]] = []
    increased = 0
    decreased = 0
    unchanged = 0
    for name in all_names:
        base_row = base_items.get(name)
        compare_row = compare_items.get(name)
        base_price = base_row.unit_price if base_row else None
        compare_price = compare_row.unit_price if compare_row else None
        resolved_row = compare_row or base_row
        unit = resolved_row.unit if resolved_row is not None else ""
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
                "item_name": name,
                "unit": unit,
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
        "dimensions": ["year", "item_name"],
        "location": location or rows[0].location,
        "years": [base_year, compare_year],
        "base_year": base_year,
        "compare_year": compare_year,
        "item_count": len(items),
        "increased_count": increased,
        "decreased_count": decreased,
        "unchanged_count": unchanged,
        "new_count": sum(1 for item in items if item["status"] == "new"),
        "removed_count": sum(1 for item in items if item["status"] == "removed"),
        "items": items,
    }


def build_welding_unit_price_drivers(
    rows: list[WeldingUnitPriceRow],
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
            "object_type": "welding_unit_price",
            "year": row.year,
            "location": row.location,
            "item_name": row.item_name,
            "unit": row.unit,
            "unit_price": _unit_price_str(row.unit_price),
        }
        for index, row in enumerate(ranked, start=1)
    ]
    return {"kind": "drivers", "items": items, "top_n": top_n}
