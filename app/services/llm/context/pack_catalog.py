"""report_type → pack_ids。"""

from __future__ import annotations

REPORT_PACK_MAP: dict[str, tuple[str, ...]] = {
    "dashboard": (
        "scope_meta",
        "month_overview",
        "l0_top_drivers",
        "l0_indirect_summary",
        "missing_price_risk",
        "mom_comparison",
    ),
    "steel": ("scope_meta", "steel_price_summary", "mom_comparison"),
    "stamping_part": (
        "scope_meta",
        "stamping_cost_summary",
        "missing_price_risk",
    ),
    "l0": (
        "scope_meta",
        "l0_top_drivers",
        "l0_indirect_summary",
        "mom_comparison",
    ),
    "part_drilldown": ("scope_meta", "part_drilldown"),
    "gate": ("scope_meta", "engine_gate_digest"),
    "exec_brief": (
        "scope_meta",
        "month_overview",
        "l0_top_drivers",
        "missing_price_risk",
    ),
}

# Pack 装包常量（防 token 爆炸）
L0_FETCH_LIMIT = 200
TOP_N = 10
MISSING_SAMPLE_LIMIT = 20
STEEL_FETCH_LIMIT = 100
STAMPING_FETCH_LIMIT = 100


def pack_ids_for(report_type: str) -> tuple[str, ...]:
    packs = REPORT_PACK_MAP.get(report_type)
    if packs is None:
        return REPORT_PACK_MAP["dashboard"]
    return packs
