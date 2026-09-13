"""L0 月汇总：始终从明细表实时聚合。"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.database import DatabaseConfig
from app.repositories.llm.cost_analysis import L0CostAnalysisRepository
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.context.snapshot_builder import SnapshotBuilder
from app.services.llm.query.query_parser import QueryParser


@pytest.mark.integration
def test_monthly_totals_and_summary_from_l0_detail() -> None:
    """青岛 2025 全年：12 个月、27 件、与明细表一致。"""
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
        assert len(monthly) == 12
        assert monthly[0].l0_count == 27
        assert monthly[0].grand_total_sum.quantize(Decimal("0.01")) == Decimal("1381.99")

        query = QueryParser().parse(db, user_question="2025年，青岛的核算情况？")
        run = AnalysisRunner().run(db, query)
        snapshot = SnapshotBuilder().build(query=query, run=run)
        summary = run.summary or {}
        assert summary.get("l0_count") == 27
        assert summary.get("month_count") == 12
        assert snapshot.meta.scope is not None
        assert snapshot.meta.scope.is_full_calendar_year is True
    finally:
        db.close()
