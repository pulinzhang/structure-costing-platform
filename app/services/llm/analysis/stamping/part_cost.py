"""冲压零件价下钻（主题内公开函数，assembly 可引用）。"""

from __future__ import annotations

from app.common.part_number import part_numbers_match
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
from app.schemas.llm.analysis_payload import (
    DrilldownPayload,
)


def build_stamping_cost_drilldown(
    rows: list[StampingPartPeriodRow],
    *,
    part_number: str,
) -> DrilldownPayload:
    matched = (
        [row for row in rows if part_numbers_match(row.part_number, part_number)]
        if part_number
        else rows
    )
    if not matched:
        return {
            "kind": "drilldown",
            "part_number": part_number,
            "found": False,
            "message": "未找到该冲压零件价格记录",
        }
    latest = sorted(matched, key=lambda row: (row.year, row.month))[-1]
    return {
        "kind": "drilldown",
        "part_number": latest.part_number,
        "found": True,
        "part_name": latest.part_name,
        "unit_cost": str(latest.unit_cost),
        "material_net_per_part": (
            str(latest.material_net_per_part) if latest.material_net_per_part is not None else None
        ),
        "process_fee_amount": (
            str(latest.process_fee_amount) if latest.process_fee_amount is not None else None
        ),
        "die_fee_amount": (
            str(latest.die_fee_amount) if latest.die_fee_amount is not None else None
        ),
        "gauge_fee_amount": (
            str(latest.gauge_fee_amount) if latest.gauge_fee_amount is not None else None
        ),
        "calc_status": latest.calc_status,
        "stamping_supplier": latest.stamping_supplier,
        "month": f"{latest.year:04d}-{latest.month:02d}",
    }
