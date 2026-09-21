"""冲压加工费问句解析与取数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.parser.pipeline import QueryParser


def test_query_parser_stamping_process_fee_subject() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["芜湖", "青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛", "芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T13J"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V3"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=["502008024AA"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-08"},
            "filters": {"part_number": "8024"},
            "compare_locations": [],
        }
    )

    query = parser.parse(db, user_question="今年，8024，冲压费加工费多少")
    assert query.subject == "stamping_process_fee"
    assert query.part_number() == "502008024AA"
    assert "drilldown" in query.analyses


@pytest.mark.integration
def test_stamping_process_fee_lookup_8024() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(db, user_question="今年，8024，冲压费加工费多少")
        assert query.subject == "stamping_process_fee"

        run = AnalysisRunner().run(db, query)
        if not run.has_data:
            pytest.skip(run.data_message or "当前范围无冲压加工费")
        assert run.summary is not None
        assert run.summary["row_count"] >= 1

        result = run.result
        if result.get("kind") == "composite":
            drill = (result.get("parts") or {}).get("drilldown") or {}
        else:
            drill = result
        assert drill.get("found") is True
        assert drill.get("part_number") == "502008024AA"
        assert drill.get("final_processing_fee") == "1.508"
        assert drill.get("year") == 2026
    finally:
        db.close()
