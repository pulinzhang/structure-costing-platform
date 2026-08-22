"""焊接工艺拆解 summary / drilldown / drivers。"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.repositories.llm.welding_process_breakdown_analysis_repository import (
    WeldingBreakdownNodeRow,
)


def _qty_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


def build_welding_breakdown_summary(rows: list[WeldingBreakdownNodeRow]) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "welding_process_breakdown",
            "node_count": 0,
            "part_count": 0,
            "locations": [],
            "vehicle_models": [],
            "bom_versions": [],
            "zero_process_count": 0,
        }

    zero_process = sum(1 for row in rows if row.process_line_count <= 0)
    return {
        "subject": "welding_process_breakdown",
        "node_count": len(rows),
        "part_count": len({row.part_number for row in rows}),
        "locations": sorted({row.location for row in rows}),
        "vehicle_models": sorted({row.vehicle_model for row in rows}),
        "bom_versions": sorted({row.bom_version for row in rows}),
        "zero_process_count": zero_process,
    }


def build_welding_breakdown_drilldown(
    rows: list[WeldingBreakdownNodeRow],
    *,
    part_token: str,
    head: WeldingBreakdownNodeRow | None = None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的焊接工艺拆解节点",
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
        "location": best.location,
        "vehicle_model": best.vehicle_model,
        "bom_version": best.bom_version,
        "level": best.level,
        "assembly_qty": _qty_str(best.assembly_qty),
        "process_line_count": best.process_line_count,
        "parse_status": best.parse_status,
        "audit_status": best.audit_status,
        "items": [
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "process_line_count": row.process_line_count,
                "assembly_qty": _qty_str(row.assembly_qty),
                "parse_status": row.parse_status,
            }
            for row in rows[:20]
        ],
    }


def build_welding_breakdown_drivers(
    rows: list[WeldingBreakdownNodeRow],
    *,
    top_n: int = 8,
) -> dict[str, Any]:
    if not rows:
        return {"kind": "drivers", "items": [], "top_n": top_n}

    ranked = sorted(rows, key=lambda row: row.process_line_count, reverse=True)[:top_n]
    items = [
        {
            "rank": index,
            "object_type": "welding_process_breakdown",
            "part_number": row.part_number,
            "part_name": row.part_name,
            "process_line_count": row.process_line_count,
            "location": row.location,
            "vehicle_model": row.vehicle_model,
            "bom_version": row.bom_version,
        }
        for index, row in enumerate(ranked, start=1)
    ]
    return {"kind": "drivers", "items": items, "top_n": top_n}
