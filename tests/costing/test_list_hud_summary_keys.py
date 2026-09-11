"""列表 HUD summary 字段契约：改看板口径时先改这里，再改 Repository / 前端。"""

from app.repositories.bom.procurement_object_repository import empty_procurement_object_summary
from app.repositories.costing.assembly_cost.assembly_cost_repository import (
    empty_assembly_cost_summary,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    empty_part_cost_summary,
)


def test_part_cost_hud_summary_keys() -> None:
    assert set(empty_part_cost_summary()) == {
        "unit_cost_sum",
        "avg_unit_cost",
        "material_net_per_part_sum",
        "process_fee_amount_sum",
        "pending_count",
        "approved_count",
    }


def test_assembly_cost_hud_summary_keys() -> None:
    assert set(empty_assembly_cost_summary()) == {
        "total_count",
        "ok_count",
        "partial_count",
        "pending_count",
        "approved_count",
        "grand_total_sum",
        "total_amount_sum",
        "avg_grand_total",
        "material_amount_sum",
        "welding_amount_sum",
    }


def test_procurement_object_hud_summary_keys() -> None:
    assert set(empty_procurement_object_summary()) == {
        "total_count",
        "pending_count",
        "approved_count",
        "object_count",
        "object_l0_degenerate_count",
        "other_leaf_count",
        "anomaly_count",
    }
