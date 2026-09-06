"""冲压加工费 summary / drilldown。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.repositories.llm.process_fee_analysis_repository import ProcessFeeRow


def _fee_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return f"{quantized:.3f}"


def build_process_fee_summary(rows: list[ProcessFeeRow]) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "stamping_process_fee",
            "row_count": 0,
            "part_count": 0,
            "years": [],
            "processing_fee_min": "0.000",
            "processing_fee_max": "0.000",
            "final_processing_fee_avg": "0.000",
        }

    part_numbers = {row.part_number for row in rows}
    years = sorted({row.year for row in rows})
    fees = [row.final_processing_fee or row.processing_fee or Decimal("0") for row in rows]
    fee_sum = sum(fees, Decimal("0"))
    avg = fee_sum / len(fees) if fees else Decimal("0")

    return {
        "subject": "stamping_process_fee",
        "row_count": len(rows),
        "part_count": len(part_numbers),
        "years": years,
        "processing_fee_min": _fee_str(min(fees)) or "0.000",
        "processing_fee_max": _fee_str(max(fees)) or "0.000",
        "final_processing_fee_avg": _fee_str(avg) or "0.000",
    }


def build_process_fee_drilldown(
    rows: list[ProcessFeeRow],
    *,
    part_token: str,
    head: ProcessFeeRow | None = None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的冲压加工费记录",
            "query_token": part_token,
            "items": [],
        }

    best = head or rows[0]
    items = [
        {
            "year": row.year,
            "location": row.location,
            "stamping_supplier": row.stamping_supplier,
            "vehicle_model": row.vehicle_model,
            "version": row.version,
            "part_number": row.part_number,
            "part_name": row.part_name,
            "processing_fee": _fee_str(row.processing_fee),
            "other_fee": _fee_str(row.other_fee),
            "final_processing_fee": _fee_str(row.final_processing_fee),
            "process_count": row.process_count,
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
        "stamping_supplier": best.stamping_supplier,
        "vehicle_model": best.vehicle_model,
        "version": best.version,
        "processing_fee": _fee_str(best.processing_fee),
        "other_fee": _fee_str(best.other_fee),
        "final_processing_fee": _fee_str(best.final_processing_fee),
        "process_count": best.process_count,
        "audit_status": best.audit_status,
        "items": items,
    }
