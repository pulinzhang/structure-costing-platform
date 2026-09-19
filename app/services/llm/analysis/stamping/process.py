"""冲压工艺 summary / drivers / drilldown。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.repositories.llm.stamping_process_analysis_repository import (
    StampingProcessDetailRow,
    StampingProcessPartRow,
)
from app.schemas.llm.analysis_payload import (
    DrilldownPayload,
    DriverItem,
    SummaryPayload,
)


def build_stamping_process_summary(rows: list[StampingProcessPartRow]) -> SummaryPayload:
    if not rows:
        return {
            "subject": "stamping_process",
            "part_count": 0,
            "process_count": 0,
            "avg_process_count": "0.00",
            "tailor_welded_count": 0,
            "parts_without_process": 0,
            "max_tonnage": None,
            "location_count": 0,
            "vehicle_model_count": 0,
        }

    process_total = sum(row.process_count for row in rows)
    without_process = sum(1 for row in rows if row.process_count == 0)
    tailor_welded = sum(1 for row in rows if row.is_tailor_welded)
    tonnages = [row.max_tonnage for row in rows if row.max_tonnage is not None]
    locations = {row.location for row in rows}
    vehicle_models = {row.vehicle_model for row in rows}
    avg = Decimal(process_total) / Decimal(len(rows))

    return {
        "subject": "stamping_process",
        "part_count": len(rows),
        "process_count": process_total,
        "avg_process_count": f"{avg.quantize(Decimal('0.01'))}",
        "tailor_welded_count": tailor_welded,
        "parts_without_process": without_process,
        "max_tonnage": max(tonnages) if tonnages else None,
        "location_count": len(locations),
        "vehicle_model_count": len(vehicle_models),
    }


def build_stamping_process_drivers(
    rows: list[StampingProcessPartRow],
    *,
    top_n: int = 15,
) -> SummaryPayload:
    """工序数最多的零件 TopN。"""
    ranked_rows = sorted(
        [row for row in rows if row.process_count > 0],
        key=lambda row: (row.process_count, row.part_number),
        reverse=True,
    )[:top_n]

    items: list[DriverItem] = []
    for index, row in enumerate(ranked_rows, start=1):
        items.append(
            {
                "rank": index,
                "object_type": "stamping_process",
                "part_number": row.part_number,
                "part_name": row.part_name,
                "process_count": row.process_count,
                "max_tonnage": row.max_tonnage,
                "vehicle_model": row.vehicle_model,
                "version": row.version,
                "location": row.location,
            }
        )
    return {"kind": "drivers", "items": items, "top_n": top_n}


def build_stamping_process_drilldown(
    part: StampingProcessPartRow | None,
    processes: list[StampingProcessDetailRow],
    *,
    part_number: str,
) -> DrilldownPayload:
    if part is None:
        return {
            "kind": "drilldown",
            "part_number": part_number,
            "found": False,
            "message": "未找到该冲压工艺零件",
        }

    by_tonnage: dict[int, int] = defaultdict(int)
    for row in processes:
        if row.tonnage is not None:
            by_tonnage[row.tonnage] += 1

    return {
        "kind": "drilldown",
        "part_number": part.part_number,
        "found": True,
        "part_name": part.part_name,
        "location": part.location,
        "vehicle_model": part.vehicle_model,
        "version": part.version,
        "material": part.material,
        "thickness": str(part.thickness) if part.thickness is not None else None,
        "is_tailor_welded": part.is_tailor_welded,
        "process_count": part.process_count,
        "processes": [
            {
                "process_seq": row.process_seq,
                "process_order": row.process_order,
                "process_code": row.process_code,
                "tonnage": row.tonnage,
                "die_sets": row.die_sets,
            }
            for row in processes
        ],
        "tonnage_distribution": [
            {"tonnage": tonnage, "step_count": count}
            for tonnage, count in sorted(by_tonnage.items())
        ],
    }
