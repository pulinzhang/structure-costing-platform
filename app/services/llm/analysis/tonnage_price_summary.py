"""冲次单价 summary / drilldown。"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.repositories.llm.tonnage_price_analysis_repository import TonnagePriceRow


def _price_str(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return f"{quantized:.3f}"


def build_tonnage_price_summary(rows: list[TonnagePriceRow]) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "stamping_tonnage",
            "row_count": 0,
            "location_count": 0,
            "tonnage_count": 0,
            "years": [],
            "price_per_stroke_min": "0.000",
            "price_per_stroke_max": "0.000",
        }

    locations = {row.location for row in rows}
    tonnages = {row.tonnage for row in rows}
    years = sorted({row.year for row in rows})
    prices = [row.price_per_stroke for row in rows]

    return {
        "subject": "stamping_tonnage",
        "row_count": len(rows),
        "location_count": len(locations),
        "tonnage_count": len(tonnages),
        "years": years,
        "price_per_stroke_min": _price_str(min(prices)),
        "price_per_stroke_max": _price_str(max(prices)),
    }


def build_tonnage_price_drilldown(
    rows: list[TonnagePriceRow],
    *,
    tonnage: int | None,
) -> dict[str, Any]:
    matched = [row for row in rows if row.tonnage == tonnage] if tonnage is not None else list(rows)

    if not matched:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的冲次单价记录",
            "tonnage": tonnage,
            "items": [],
        }

    items = [
        {
            "location": row.location,
            "year": row.year,
            "tonnage": row.tonnage,
            "price_per_stroke": _price_str(row.price_per_stroke),
            "audit_status": row.audit_status,
        }
        for row in matched
    ]
    head = matched[0]
    return {
        "kind": "drilldown",
        "found": True,
        "tonnage": head.tonnage,
        "location": head.location,
        "year": head.year,
        "price_per_stroke": _price_str(head.price_per_stroke),
        "audit_status": head.audit_status,
        "items": items,
    }
