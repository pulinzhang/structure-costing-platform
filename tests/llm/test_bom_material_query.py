"""材料清单 / 产品结构问句解析与取数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.query_parser import QueryParser


def test_query_parser_bom_material_subject() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛", "芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["D/00"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地", "vehicle_model": "T28"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="青岛基地，T28，材料清单的情况。",
    )
    assert query.subject == "bom_material"
    assert query.location() == "青岛"


@pytest.mark.integration
def test_bom_material_qingdao_t28() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(
            db,
            user_question="青岛基地，T28，材料清单的情况。",
        )
        assert query.subject == "bom_material"

        run = AnalysisRunner().run(db, query)
        assert run.has_data is True
        assert run.summary is not None
        assert run.summary["node_count"] > 0
        assert "青岛" in run.summary["locations"]
    finally:
        db.close()
