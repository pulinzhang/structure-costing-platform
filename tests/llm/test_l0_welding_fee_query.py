# -*- coding: utf-8 -*-
"""成品焊接费问句解析与取数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.query_parser import QueryParser


def test_query_parser_l0_welding_fee_subject() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(  # noqa: SLF001
        return_value=["青岛"]
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(  # noqa: SLF001
        return_value=["T28"]
    )
    parser._aligner._scope_repo.list_bom_versions = MagicMock(  # noqa: SLF001
        return_value=["D/00"]
    )
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2026-08"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="今年与去年，青岛基地，成品焊接费，比较。",
    )
    assert query.subject == "l0_welding_fee"
    assert query.location() == "青岛"
    assert "comparison" in query.analyses


@pytest.mark.integration
def test_l0_welding_fee_qingdao_yoy() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(
            db,
            user_question="今年与去年，青岛基地，成品焊接费，比较。",
        )
        assert query.subject == "l0_welding_fee"

        run = AnalysisRunner().run(db, query)
        assert run.has_data is True
        assert run.summary is not None
        assert run.summary["row_count"] > 0
        assert len(run.summary["years"]) >= 2
    finally:
        db.close()
