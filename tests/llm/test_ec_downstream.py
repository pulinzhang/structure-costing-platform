"""工程变更下游齐套 / 工艺布点到期 leaf 构建。"""

from __future__ import annotations

from app.repositories.llm.engineering_change_effect_analysis_repository import (
    EngineeringChangeDownstreamRow,
    ProcessDiePeriodRow,
    build_ec_downstream_completeness,
    build_ec_process_die_period,
)


def test_build_ec_downstream_completeness() -> None:
    rows = [
        EngineeringChangeDownstreamRow(
            upload_log_id=1,
            change_order_id=10,
            location="青岛",
            vehicle_model="T28",
            effective_year=2025,
            effective_month=7,
            change_type="改图",
            before_part_number="A",
            after_part_number="B",
            before_assembly_part_number="ASM",
            after_assembly_part_number="ASM2",
            process_inserted_count=2,
            die_inserted_count=1,
            procurement_object_inserted_count=3,
            welding_breakdown_inserted_count=1,
            effect_kinds=("process_part", "procurement_object"),
        ),
        EngineeringChangeDownstreamRow(
            upload_log_id=1,
            change_order_id=11,
            location="青岛",
            vehicle_model="T28",
            effective_year=2025,
            effective_month=7,
            change_type="增加零件",
            before_part_number=None,
            after_part_number="C",
            before_assembly_part_number="ASM",
            after_assembly_part_number="ASM",
            process_inserted_count=2,
            die_inserted_count=1,
            procurement_object_inserted_count=3,
            welding_breakdown_inserted_count=1,
            effect_kinds=("procurement_object",),
        ),
    ]
    payload = build_ec_downstream_completeness(rows)
    assert payload["missing_process_link_count"] == 1
    assert payload["process_inserted_count"] == 2
    assert payload["procurement_object_inserted_count"] == 3


def test_build_ec_process_die_period() -> None:
    rows = [
        ProcessDiePeriodRow(
            kind="process_before",
            part_id=1,
            part_number="OLD",
            part_name="旧工艺",
            location="青岛",
            vehicle_model="T28",
            effective_year=2024,
            effective_month=1,
            expiry_year=2025,
            expiry_month=6,
            is_active_at_ec=False,
            link_id=10,
        ),
        ProcessDiePeriodRow(
            kind="process_after",
            part_id=2,
            part_number="NEW",
            part_name="新工艺",
            location="青岛",
            vehicle_model="T28",
            effective_year=2025,
            effective_month=7,
            expiry_year=None,
            expiry_month=None,
            is_active_at_ec=True,
            link_id=10,
        ),
        ProcessDiePeriodRow(
            kind="die_before",
            part_id=3,
            part_number="OLD-DIE",
            part_name="旧布点",
            location="青岛",
            vehicle_model="T28",
            effective_year=2024,
            effective_month=1,
            expiry_year=2025,
            expiry_month=6,
            is_active_at_ec=False,
            link_id=20,
        ),
        ProcessDiePeriodRow(
            kind="die_after",
            part_id=4,
            part_number="NEW-DIE",
            part_name="新布点",
            location="青岛",
            vehicle_model="T28",
            effective_year=2025,
            effective_month=7,
            expiry_year=None,
            expiry_month=None,
            is_active_at_ec=True,
            link_id=20,
        ),
    ]
    payload = build_ec_process_die_period(rows)
    assert payload["expired_before_count"] == 2
    assert payload["active_after_count"] == 2
    assert payload["die_before_without_after_count"] == 0
    assert "未见有旧无新" in str(payload["message"])
