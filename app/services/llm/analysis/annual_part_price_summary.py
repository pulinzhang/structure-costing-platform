"""年度零件价 summary / comparison / drilldown / drivers。"""

from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.repositories.llm.annual_part_price_analysis_repository import AnnualPartPriceRow
from app.services.llm.analysis.constants import (
    ANNUAL_PRICE_CONVERSION_FACTOR_MIN,
    ANNUAL_PRICE_CONVERSION_TOLERANCE,
)

_PRICE_QUANT = Decimal("0.0001")
_FINE_COSTING_UNITS = frozenset({"mm", "cm", "g", "ml", "毫克", "毫升", "毫米", "厘米"})
_BULK_PURCHASE_UNITS = frozenset({"桶", "瓶", "罐", "kg", "KG", "公斤", "升", "L", "l", "盒", "箱"})


def _unit_price_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(_PRICE_QUANT, rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


def _round4(value: Decimal) -> Decimal:
    return value.quantize(_PRICE_QUANT, rounding=ROUND_HALF_UP)


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
            "purchase_unit": row.purchase_unit,
            "purchase_unit_price": _unit_price_str(row.purchase_unit_price),
            "conversion_factor": str(row.conversion_factor),
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
        "purchase_unit": best.purchase_unit,
        "purchase_unit_price": _unit_price_str(best.purchase_unit_price),
        "conversion_factor": str(best.conversion_factor),
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


def build_annual_part_price_conversion_anomalies(
    rows: list[AnnualPartPriceRow],
    *,
    top_n: int = 20,
) -> dict[str, Any]:
    """核价单价应 = 采购单价 ÷ 转换系数。未除系数会把桶价当成毫米价。"""
    factor_min = Decimal(ANNUAL_PRICE_CONVERSION_FACTOR_MIN)
    tolerance = Decimal(ANNUAL_PRICE_CONVERSION_TOLERANCE)
    items: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()
    for row in rows:
        flags = _conversion_flags(row, factor_min=factor_min, tolerance=tolerance)
        if not flags:
            continue
        key = (row.year, row.location, row.part_number)
        if key in seen:
            continue
        seen.add(key)
        purchase = row.purchase_unit_price
        factor = row.conversion_factor if row.conversion_factor > 0 else Decimal("1")
        derived = _round4(purchase / factor) if purchase is not None and purchase > 0 else None
        items.append(
            {
                "anomaly_type": flags[0],
                "anomaly_flags": flags,
                "year": row.year,
                "location": row.location,
                "part_number": row.part_number,
                "part_name": row.part_name,
                "supply_type": row.supply_type,
                "purchase_unit": row.purchase_unit,
                "purchase_unit_price": _unit_price_str(purchase),
                "conversion_factor": str(factor),
                "unit": row.unit,
                "unit_price": _unit_price_str(row.unit_price),
                "expected_unit_price": _unit_price_str(derived),
                "message": _conversion_message(flags[0], row.unit, factor),
            }
        )
    items.sort(key=lambda item: (item["anomaly_type"], item["part_number"]))
    return {
        "kind": "annual_price_anomalies",
        "threshold": str(tolerance),
        "conversion_factor_min": str(factor_min),
        "items": items[:top_n],
    }


def annual_price_conversion_risk_entry(payload: dict[str, Any]) -> dict[str, Any] | None:
    items = list(payload.get("items") or [])
    if not items:
        return None
    return {
        "risk_type": "annual_price_conversion",
        "severity": "high",
        "count": len(items),
        "message": "年度零件价存在未按转换系数换算的核价单价（桶/瓶价可能被当成毫米单价）",
        "sample_part_numbers": [item["part_number"] for item in items[:8]],
        "conversion_items": items,
    }


def _conversion_flags(
    row: AnnualPartPriceRow,
    *,
    factor_min: Decimal,
    tolerance: Decimal,
) -> list[str]:
    flags: list[str] = []
    factor = row.conversion_factor if row.conversion_factor > 0 else Decimal("1")
    purchase = row.purchase_unit_price
    unit_key = (row.unit or "").strip().lower()
    purchase_unit = (row.purchase_unit or "").strip()
    is_fine_unit = unit_key in _FINE_COSTING_UNITS or (row.unit or "") in _FINE_COSTING_UNITS

    if purchase is not None and purchase > 0 and factor >= factor_min:
        ratio = row.unit_price / purchase
        derived = _round4(purchase / factor)
        if Decimal("0.5") <= ratio <= Decimal("2"):
            flags.append("skipped_conversion")
        elif derived > 0:
            error = abs(row.unit_price - derived) / derived
            if error >= tolerance:
                flags.append("conversion_mismatch")

    if (
        is_fine_unit
        and factor <= Decimal("1")
        and purchase_unit in _BULK_PURCHASE_UNITS
        and row.unit_price >= Decimal("0.01")
    ):
        flags.append("fine_unit_unconverted")

    if (
        is_fine_unit
        and row.unit_price >= Decimal("0.01")
        and "skipped_conversion" not in flags
        and "fine_unit_unconverted" not in flags
        and (
            factor >= factor_min
            or (purchase is not None and row.unit_price >= purchase * Decimal("0.5"))
        )
    ):
        flags.append("fine_unit_high_price")

    return flags


def _conversion_message(anomaly_type: str, unit: str, factor: Decimal) -> str:
    if anomaly_type == "skipped_conversion":
        return (
            f"核价单价与采购单价几乎相同，未除转换系数 {factor}；"
            f"若核价单位是 {unit}，成本会放大约 {factor} 倍"
        )
    if anomaly_type == "fine_unit_unconverted":
        return f"采购按桶/瓶，核价单位是 {unit}，但转换系数为 1，毫米/克单价可能被当成采购价"
    if anomaly_type == "fine_unit_high_price":
        return f"核价单位是 {unit}，核价单价偏高，请核是否把采购单价填进了毫米单价"
    return "核价单价与「采购单价÷转换系数」不一致"
