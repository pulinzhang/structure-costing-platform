"""总成材料构成独大：一条明细占应成本过大。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.repositories.llm.cost_analysis_repository import L0CompositionLineRow
from app.services.llm._money import money_str, month_key, rate_str
from app.services.llm.analysis.constants import (
    COMPOSITION_EXTREME_QTY,
    COMPOSITION_SHARE_THRESHOLD,
)

_PRICE_QUANT = Decimal("0.0001")
_COST_SOURCE_LABEL = {
    "annual": "外购件",
    "bundle": "一口价",
    "stamping": "自制冲压",
    "missing": "缺价",
    "skipped_by_bundle": "一口价剪枝",
}


def _unit_price_str(value: Decimal) -> str:
    return f"{value.quantize(_PRICE_QUANT):.4f}"


def build_composition_anomalies(
    lines: list[L0CompositionLineRow],
    *,
    top_n: int = 15,
    min_share: Decimal | None = None,
    extreme_qty: Decimal | None = None,
) -> dict[str, Any]:
    share_threshold = min_share if min_share is not None else Decimal(COMPOSITION_SHARE_THRESHOLD)
    qty_threshold = extreme_qty if extreme_qty is not None else Decimal(COMPOSITION_EXTREME_QTY)
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for line in lines:
        if line.root_should_cost <= 0 or line.line_amount <= 0:
            continue
        share = (line.line_amount / line.root_should_cost).quantize(Decimal("0.0001"))
        is_dominant = share >= share_threshold
        is_extreme_qty = line.effective_qty >= qty_threshold and share >= Decimal("0.20")
        if not is_dominant and not is_extreme_qty:
            continue
        key = (month_key(line.year, line.month), line.root_part_number, line.child_part_number)
        if key in seen:
            continue
        seen.add(key)
        anomaly_type = "composition_dominance" if is_dominant else "extreme_qty"
        items.append(
            {
                "anomaly_type": anomaly_type,
                "month": month_key(line.year, line.month),
                "root_part_number": line.root_part_number,
                "root_part_name": line.root_part_name,
                "root_should_cost": money_str(line.root_should_cost),
                "child_part_number": line.child_part_number,
                "child_part_name": line.child_part_name,
                "cost_source": line.cost_source,
                "cost_source_label": _COST_SOURCE_LABEL.get(line.cost_source, line.cost_source),
                "unit_price": _unit_price_str(line.unit_price),
                "effective_qty": str(line.effective_qty),
                "line_amount": money_str(line.line_amount),
                "share_of_should_cost": rate_str(share),
            }
        )

    items.sort(
        key=lambda item: Decimal(str(item["share_of_should_cost"] or 0)),
        reverse=True,
    )
    return {
        "kind": "composition_anomalies",
        "threshold": str(share_threshold),
        "extreme_qty_threshold": str(qty_threshold),
        "items": items[:top_n],
    }


def composition_risk_entry(payload: dict[str, Any]) -> dict[str, Any] | None:
    items = list(payload.get("items") or [])
    if not items:
        return None
    return {
        "risk_type": "composition_dominance",
        "severity": "high",
        "count": len(items),
        "message": "存在材料明细占应成本过大的总成（单件独大或用量异常）",
        "sample_part_numbers": [item["root_part_number"] for item in items[:8]],
        "composition_items": items,
    }
