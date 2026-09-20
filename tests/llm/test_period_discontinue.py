"""核价旁挂停用件（完成停止 / 此件不装）。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.repositories.llm.engineering_change_analysis_repository import EngineeringChangeRow
from app.services.llm.analysis.shared.period_discontinue import (
    build_period_discontinue,
    period_discontinue_risk_entry,
    should_attach_period_discontinue,
)


def test_should_attach_period_discontinue_for_summary() -> None:
    assert should_attach_period_discontinue(
        analyses=["summary"], asks_part_price=False, part_number=None
    )
    assert should_attach_period_discontinue(
        analyses=["risk", "trend"], asks_part_price=False, part_number=None
    )


def test_should_skip_period_discontinue_for_part_price() -> None:
    assert not should_attach_period_discontinue(
        analyses=["drilldown"], asks_part_price=True, part_number="2856"
    )


def test_build_period_discontinue_empty() -> None:
    db = MagicMock()
    with patch(
        "app.services.llm.analysis.shared.period_discontinue._repo.query_rows",
        return_value=[],
    ):
        payload = build_period_discontinue(
            db,
            location="芜湖",
            vehicle_model="T13J",
            start_year=2026,
            start_month=1,
            end_year=2026,
            end_month=1,
        )
    assert payload["has_discontinue"] is False
    assert payload["discontinue_count"] == 0
    assert "未见" in str(payload["message"])
    assert period_discontinue_risk_entry(payload) is None


def test_build_period_discontinue_with_stop() -> None:
    db = MagicMock()
    rows = [
        EngineeringChangeRow(
            location="芜湖",
            vehicle_model="T13J",
            effective_year=2026,
            effective_month=1,
            change_type="完成停止",
            before_assembly_part_number="A-OLD",
            after_assembly_part_number=None,
            assembly_name="某总成",
            part_level="总成",
            before_part_number=None,
            after_part_number=None,
            part_name=None,
            project_code="T13J",
            status="active",
        ),
        EngineeringChangeRow(
            location="芜湖",
            vehicle_model="T13J",
            effective_year=2026,
            effective_month=1,
            change_type="此件不装",
            before_assembly_part_number="B-ASM",
            after_assembly_part_number="B-ASM-NEW",
            assembly_name="后围",
            part_level="一级",
            before_part_number="P-OLD",
            after_part_number=None,
            part_name="胶块",
            project_code="T13J",
            status="active",
        ),
    ]
    with patch(
        "app.services.llm.analysis.shared.period_discontinue._repo.query_rows",
        return_value=rows,
    ):
        payload = build_period_discontinue(
            db,
            location="芜湖",
            vehicle_model="T13J",
            start_year=2026,
            start_month=1,
            end_year=2026,
            end_month=1,
        )
    assert payload["has_discontinue"] is True
    assert payload["stop_count"] == 1
    assert payload["not_install_count"] == 1
    assert "不是算错" in str(payload["message"])
    risk = period_discontinue_risk_entry(payload)
    assert risk is not None
    assert risk["risk_type"] == "period_discontinue"
    assert risk["count"] == 2
