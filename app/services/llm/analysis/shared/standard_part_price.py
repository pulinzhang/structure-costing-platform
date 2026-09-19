"""标准件 / 胶块计件单价：通常几分钱，过大即异常。"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app.schemas.llm.analysis_payload import DomainAnomaliesPayload, RiskEntry
from app.services.llm.analysis.shared.constants import (
    STANDARD_PART_NAME_KEYS,
    STANDARD_PART_SUPPLY_TYPES,
    STANDARD_PART_UNIT_PRICE_MAX,
)

_PRICE_QUANT = Decimal("0.0001")
_FINE_UNITS = frozenset({"mm", "cm", "g", "ml", "毫克", "毫升", "毫米", "厘米"})
_PIECE_UNITS = frozenset({"pcs", "pc", "ea", "件", "个"})


def _unit_price_str(value: Decimal) -> str:
    return f"{value.quantize(_PRICE_QUANT):.4f}"


def is_piece_standard_part(
    *,
    supply_type: str | None,
    part_name: str | None,
    unit: str | None,
) -> bool:
    unit_key = (unit or "").strip().lower()
    unit_raw = (unit or "").strip()
    if unit_key in _FINE_UNITS or unit_raw in _FINE_UNITS:
        return False
    if unit_key and unit_key not in _PIECE_UNITS and unit_raw not in _PIECE_UNITS:
        return False
    supply = (supply_type or "").strip()
    if supply in STANDARD_PART_SUPPLY_TYPES:
        return True
    name = part_name or ""
    return any(key in name for key in STANDARD_PART_NAME_KEYS)


def build_standard_part_price_anomalies(
    rows: Sequence[object],
    *,
    top_n: int = 20,
) -> DomainAnomaliesPayload:
    """计件标准件 / 胶块核价单价过大。行对象需有 part_number、unit_price。"""
    threshold = Decimal(STANDARD_PART_UNIT_PRICE_MAX)
    items: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for row in rows:
        unit_price = Decimal(str(getattr(row, "unit_price", 0) or 0))
        if unit_price < threshold:
            continue
        if not is_piece_standard_part(
            supply_type=getattr(row, "supply_type", None),
            part_name=getattr(row, "part_name", None) or getattr(row, "child_part_name", None),
            unit=getattr(row, "unit", None) or "pcs",
        ):
            continue
        year = getattr(row, "year", None)
        location = getattr(row, "location", None)
        month = getattr(row, "month", None)
        part_number = str(
            getattr(row, "part_number", None) or getattr(row, "child_part_number", "") or ""
        )
        key = (year, location, month, part_number)
        if key in seen:
            continue
        seen.add(key)
        part_name = getattr(row, "part_name", None) or getattr(row, "child_part_name", None)
        items.append(
            {
                "anomaly_type": "standard_part_high_price",
                "year": year,
                "month": month,
                "location": location,
                "root_part_number": getattr(row, "root_part_number", None),
                "root_part_name": getattr(row, "root_part_name", None),
                "part_number": part_number,
                "part_name": part_name,
                "supply_type": getattr(row, "supply_type", None),
                "unit": getattr(row, "unit", None) or "pcs",
                "unit_price": _unit_price_str(unit_price),
                "threshold": str(threshold),
                "message": (
                    f"标准件/胶块计件核价单价 {_unit_price_str(unit_price)} 元，"
                    f"通常几分钱，达到 {threshold} 元视为过大"
                ),
            }
        )
    items.sort(key=lambda item: Decimal(str(item["unit_price"])), reverse=True)
    return {
        "kind": "standard_part_anomalies",
        "threshold": str(threshold),
        "items": items[:top_n],
    }


def standard_part_price_risk_entry(payload: DomainAnomaliesPayload) -> RiskEntry | None:
    items = list(payload.get("items") or [])
    if not items:
        return None
    return {
        "risk_type": "standard_part_high_price",
        "severity": "high",
        "count": len(items),
        "message": "标准件/胶块（螺母、螺栓等）计件单价过大，通常应为几分钱",
        "sample_part_numbers": [
            item.get("part_number") if isinstance(item, dict) else None for item in items[:8]
        ],
        "standard_part_items": items,
    }
