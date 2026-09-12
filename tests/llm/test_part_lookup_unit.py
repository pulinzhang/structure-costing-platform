"""part_lookup 分析单测。"""

from __future__ import annotations

from decimal import Decimal

from app.repositories.llm.cost_analysis_repository import L0PartPeriodRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
from app.repositories.llm.stamping_process_analysis_repository import StampingProcessPartRow
from app.services.llm.analysis.shared.part_lookup import (
    build_part_existence,
    build_part_lookup_summary,
    format_part_lookup_message,
    resolve_part_data_profile,
)


def test_build_part_existence_mixed_hits() -> None:
    process_rows = [
        StampingProcessPartRow(
            part_id=1,
            part_number="501008898AA",
            part_name="后围外板",
            location="青岛",
            vehicle_model="T28",
            version="V3",
            stamping_supplier="供应商A",
            material="HC180YD+Z",
            thickness=Decimal("0.65"),
            is_tailor_welded=False,
            process_count=5,
            max_tonnage=800,
        )
    ]
    existence = build_part_existence(
        query_token="8898",
        l0_rows=[],
        stamping_rows=[],
        process_rows=process_rows,
    )
    assert existence["exists_any"] is True
    assert existence["l0"]["found"] is False
    assert existence["stamping_cost"]["found"] is False
    assert existence["stamping_process"]["found"] is True


def test_build_part_lookup_summary() -> None:
    summary = build_part_lookup_summary(
        query_token="501008898AA",
        l0_rows=[],
        stamping_rows=[
            StampingPartPeriodRow(
                year=2025,
                month=1,
                part_number="501008898AA",
                part_name="后围外板",
                unit_cost=Decimal("16.7395"),
                material_net_per_part=None,
                process_fee_amount=None,
                calc_status="success",
                stamping_supplier="青岛",
            )
        ],
        process_rows=[],
    )
    assert summary["exists_any"] is True
    assert summary["in_stamping_cost"] is True
    assert summary["in_l0"] is False


def test_format_part_lookup_message_none() -> None:
    assert "均未命中" in format_part_lookup_message(
        l0_rows=[],
        stamping_rows=[],
        process_rows=[],
    )


def test_l0_only_profile_marks_stamping_not_applicable() -> None:
    l0_rows = [
        L0PartPeriodRow(
            year=2025,
            month=1,
            part_number="501009144AA",
            part_name="后防撞梁总成",
            grand_total=Decimal("62.4570"),
            total_amount=Decimal("57.1050"),
            indirect_amount=Decimal("5.3520"),
            stamping_amount=Decimal("0"),
            purchased_amount=Decimal("0"),
            bundle_amount=Decimal("0"),
            welding_amount=Decimal("0"),
            welding_other_fee=Decimal("0"),
            calc_status="success",
            calc_message="",
            missing_leaf_count=0,
            bom_version="D/00",
        )
    ]
    profile = resolve_part_data_profile(
        l0_rows=l0_rows,
        stamping_rows=[],
        process_rows=[],
    )
    assert profile.primary_source == "l0"
    assert profile.stamping_cost_applicable is False
    assert profile.stamping_process_applicable is False
    assert profile.domain_note

    existence = build_part_existence(
        query_token="9144",
        l0_rows=l0_rows,
        stamping_rows=[],
        process_rows=[],
    )
    assert existence["primary_source"] == "l0"
    assert existence["stamping_cost"]["applicable"] is False
    assert existence["stamping_process"]["applicable"] is False
    assert "expected_absence" in existence["stamping_cost"]
    assert "成品供货总成" in existence["stamping_cost"]["note"]

    message = format_part_lookup_message(
        l0_rows=l0_rows,
        stamping_rows=[],
        process_rows=[],
    )
    assert message == "成品核价 供货总成=1行"
    assert "冲压价=无" not in message
