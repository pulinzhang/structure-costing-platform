"""冲次单价问句解析与取数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.common.tonnage import extract_tonnage_from_text
from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.parser.pipeline import QueryParser
from app.services.llm.query.time_range import DefaultScopeMonth, normalize_time_range


def test_extract_tonnage_40t() -> None:
    assert extract_tonnage_from_text("芜湖，今年，40T，冲压的价格。") == 40


def test_normalize_time_range_jinnian() -> None:
    tr = normalize_time_range(
        user_question="芜湖今年40T冲压价格",
        default=DefaultScopeMonth(2026, 8),
    )
    assert tr.start == "2026-01"
    assert tr.end == "2026-08"


def test_query_parser_stamping_tonnage_subject() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["芜湖", "青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛", "芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V3"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-08"},
            "filters": {"location": "芜湖", "vehicle_model": "40T"},
            "compare_locations": [],
        }
    )

    query = parser.parse(db, user_question="芜湖，今年，40T，冲压的价格。")
    assert query.subject == "stamping_tonnage"
    assert query.location() == "芜湖"
    assert query.tonnage() == 40
    assert "vehicle_model" not in query.filters
    assert "drilldown" in query.analyses


@pytest.mark.integration
def test_stamping_tonnage_lookup_wuhu_40t() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(db, user_question="芜湖，今年，40T，冲压的价格。")
        assert query.subject == "stamping_tonnage"
        assert query.tonnage() == 40

        run = AnalysisRunner().run(db, query)
        assert run.has_data is True
        assert run.summary is not None
        assert run.summary["row_count"] >= 1

        result = run.result
        if result.get("kind") == "composite":
            drill = (result.get("parts") or {}).get("drilldown") or {}
        else:
            drill = result
        assert drill.get("found") is True
        assert drill.get("price_per_stroke") == "0.046"
        assert drill.get("tonnage") == 40
        assert drill.get("location") == "芜湖"
        assert drill.get("year") == 2026
    finally:
        db.close()
