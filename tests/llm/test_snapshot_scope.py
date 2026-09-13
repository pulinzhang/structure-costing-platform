"""Context Pack scope 字段与 prompt 口径。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.schemas.llm.analysis_query import AnalysisQuery, TimeRange
from app.services.llm._money import count_months_in_span
from app.services.llm.analysis.runner import AnalysisRunner, AnalysisRunResult
from app.services.llm.context.snapshot_builder import SnapshotBuilder, _build_scope
from app.services.llm.prompts.registry import PromptRegistry
from app.services.llm.query.query_parser import QueryParser


def test_count_months_in_span() -> None:
    assert count_months_in_span("2025-01", "2025-12") == 12
    assert count_months_in_span("2025-01", "2025-03") == 3
    assert count_months_in_span("2025-03", "2025-01") == 3
    assert count_months_in_span("2025-01", "2025-01") == 1


def test_to_prompt_dict_includes_top_level_scope() -> None:
    query = AnalysisQuery(
        time_range=TimeRange(start="2025-01", end="2025-12"),
        user_question="2025年青岛核算情况",
    )
    run = AnalysisRunResult(
        has_data=True,
        summary={"months": [{"month": f"2025-{m:02d}"} for m in range(1, 13)]},
    )
    snapshot = SnapshotBuilder().build(query=query, run=run)
    payload = snapshot.to_prompt_dict()

    assert payload["scope"]["time_range"] == {"start": "2025-01", "end": "2025-12"}
    assert payload["scope"]["month_count"] == 12
    assert payload["scope"]["query_month_span"] == 12
    assert payload["scope"]["is_full_calendar_year"] is True
    assert payload["meta"]["scope"] == payload["scope"]


def test_scope_not_full_year_when_only_two_months_of_data() -> None:
    query = AnalysisQuery(
        time_range=TimeRange(start="2025-01", end="2025-12"),
        user_question="2025年青岛",
    )
    run = AnalysisRunResult(
        has_data=True,
        summary={
            "months": [
                {"month": "2025-01"},
                {"month": "2025-03"},
            ],
            "month_count": 2,
        },
    )
    scope = _build_scope(query, run)
    assert scope.month_count == 2
    assert scope.query_month_span == 12
    assert scope.is_full_calendar_year is False


@pytest.mark.integration
def test_qingdao_2025_snapshot_scope_matches_database_months() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        parser = QueryParser()
        parser._extractor.extract = MagicMock(
            return_value={
                "time_range": {"start": "2025-01", "end": "2025-12"},
                "filters": {"location": "青岛基地"},
                "compare_locations": [],
            }
        )
        query = parser.parse(db, user_question="2025年青岛核算异常情况")
        run = AnalysisRunner().run(db, query)
        snapshot = SnapshotBuilder().build(query=query, run=run)
        scope = snapshot.meta.scope
        assert scope is not None
        assert scope.time_range == {"start": "2025-01", "end": "2025-12"}
        assert scope.month_count == 12
        assert scope.is_full_calendar_year is True
        assert snapshot.summary is not None
        assert snapshot.summary["grand_total_sum"] == "16415.56"
        assert snapshot.summary["l0_count"] == 27
    finally:
        db.close()


def test_prompt_manifest_includes_scope_rules() -> None:
    registry = PromptRegistry()
    resolved = registry.resolve(audience="costing")
    assert "scope.month_count" in resolved.system_prompt
    assert "禁止把「N 个月合计」写成「全年」" in resolved.system_prompt


def test_prompt_manifest_includes_operator_scenarios() -> None:
    registry = PromptRegistry()
    buyer = registry.resolve(audience="buyer")
    assert "短码问价" in buyer.system_prompt
    assert "fork=sub_assembly" in buyer.user_shell or "操作员口语" in buyer.user_shell
