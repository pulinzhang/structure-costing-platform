"""包装运输费问句解析与取数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.query_parser import QueryParser


def test_query_parser_packaging_transport_fee_subject() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛", "芜湖"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛", "芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V3"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2026-08"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="今年与去年，青岛基地，包装运输费，比较。",
    )
    assert query.subject == "packaging_transport_fee"
    assert query.location() == "青岛"
    assert "comparison" in query.analyses


@pytest.mark.integration
def test_packaging_transport_fee_qingdao_yoy() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(
            db,
            user_question="今年与去年，青岛基地，包装运输费，比较。",
        )
        assert query.subject == "packaging_transport_fee"

        run = AnalysisRunner().run(db, query)
        assert run.has_data is True
        assert run.summary is not None
        assert run.summary["row_count"] == 84
        assert run.summary["years"] == [2025]

        result = run.result
        if result.get("kind") == "composite":
            comparison = (result.get("parts") or {}).get("comparison") or {}
        else:
            comparison = result
        assert comparison.get("location") == "青岛"
        assert comparison.get("part_count") == 84
    finally:
        db.close()
