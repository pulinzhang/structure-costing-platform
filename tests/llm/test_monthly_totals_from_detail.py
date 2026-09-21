"""L0 月汇总：始终从明细表实时聚合。"""

from __future__ import annotations

import pytest

from app.database import DatabaseConfig
from app.repositories.llm.cost_analysis.repository import L0CostAnalysisRepository
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.context.snapshot_builder import SnapshotBuilder
from app.services.llm.query.parser.pipeline import QueryParser


@pytest.mark.integration
def test_monthly_totals_and_summary_from_l0_detail() -> None:
    """青岛 2025 树根核价：月汇总与问句 summary 一致。"""
    db = DatabaseConfig.get_session_factory()()
    try:
        repo = L0CostAnalysisRepository()
        monthly = repo.query_monthly_totals(
            db,
            location="青岛",
            vehicle_model=None,
            bom_version=None,
            start_year=2025,
            start_month=1,
            end_year=2025,
            end_month=12,
        )
        if not monthly:
            pytest.skip("主库无青岛 2025 树根核价")
        assert monthly[0].l0_count > 0

        query = QueryParser().parse(db, user_question="2025年，青岛的核算情况？")
        run = AnalysisRunner().run(db, query)
        if not run.has_data:
            pytest.skip(run.data_message or "主库无青岛 2025 核价")
        snapshot = SnapshotBuilder().build(query=query, run=run)
        summary = run.summary or {}
        assert int(summary.get("l0_count") or 0) > 0
        assert int(summary.get("month_count") or 0) == len(monthly)
        assert snapshot.meta.scope is not None
        if len(monthly) == 12:
            assert snapshot.meta.scope.is_full_calendar_year is True
    finally:
        db.close()
