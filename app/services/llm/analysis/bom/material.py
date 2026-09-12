"""材料清单 summary / drilldown / drivers。"""

from __future__ import annotations

from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.repositories.llm.bom_material_analysis_repository import BomMaterialNodeRow


def _qty_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


def build_bom_material_summary(rows: list[BomMaterialNodeRow]) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "bom_material",
            "node_count": 0,
            "part_count": 0,
            "locations": [],
            "vehicle_models": [],
            "bom_versions": [],
            "node_roles": {},
        }

    part_numbers = {row.part_number for row in rows}
    roles = Counter(row.node_role for row in rows)
    return {
        "subject": "bom_material",
        "node_count": len(rows),
        "part_count": len(part_numbers),
        "locations": sorted({row.location for row in rows}),
        "vehicle_models": sorted({row.vehicle_model for row in rows}),
        "bom_versions": sorted({row.bom_version for row in rows}),
        "node_roles": dict(sorted(roles.items())),
    }


def build_bom_material_drilldown(
    rows: list[BomMaterialNodeRow],
    *,
    part_token: str,
    head: BomMaterialNodeRow | None = None,
) -> dict[str, Any]:
    if not rows:
        return {
            "kind": "drilldown",
            "found": False,
            "message": "未找到匹配的材料清单节点",
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
        "node_role": best.node_role,
        "material": best.material,
        "thickness_mm": _qty_str(best.thickness_mm),
        "qty": _qty_str(best.qty),
        "items": [
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "level": row.level,
                "node_role": row.node_role,
                "material": row.material,
                "thickness_mm": _qty_str(row.thickness_mm),
                "qty": _qty_str(row.qty),
            }
            for row in rows[:20]
        ],
    }


def build_bom_material_drivers(
    rows: list[BomMaterialNodeRow],
    *,
    top_n: int = 8,
) -> dict[str, Any]:
    if not rows:
        return {"kind": "drivers", "items": [], "top_n": top_n}

    supply_rows = [row for row in rows if row.node_role == "supply"]
    ranked = supply_rows[:top_n] if supply_rows else rows[:top_n]
    items = [
        {
            "rank": index,
            "object_type": "bom_material",
            "part_number": row.part_number,
            "part_name": row.part_name,
            "node_role": row.node_role,
            "location": row.location,
            "vehicle_model": row.vehicle_model,
            "bom_version": row.bom_version,
        }
        for index, row in enumerate(ranked, start=1)
    ]
    return {"kind": "drivers", "items": items, "top_n": top_n}
