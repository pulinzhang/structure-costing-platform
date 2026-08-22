# -*- coding: utf-8 -*-
"""焊接单价问句解析与取数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.query_parser import QueryParser


def test_query_parser_welding_unit_price_subject() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(  # noqa: SLF001
        return_value=["青岛", "芜湖"]
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(  # noqa: SLF001
        return_value=["T28"]
    )
    parser._aligner._scope_repo.list_bom_versions = MagicMock(  # noqa: SLF001
        return_value=["V3"]
    )
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(  # noqa: SLF001
        return_value=[]
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
        user_question="今年与去年，青岛基地，焊接单价，比较。",
    )
    assert query.subject == "welding_unit_price"
    assert query.location() == "青岛"
    assert "comparison" in query.analyses


@pytest.mark.integration
def test_welding_unit_price_qingdao_yoy() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(
            db,
            user_question="今年与去年，青岛基地，焊接单价，比较。",
        )
        assert query.subject == "welding_unit_price"
        assert query.location() == "青岛"

        run = AnalysisRunner().run(db, query)
        assert run.has_data is True
        assert run.summary is not None
        assert run.summary["row_count"] >= 1
        assert "青岛" in run.summary["locations"]
        assert 2025 in run.summary["years"]

        result = run.result
        if result.get("kind") == "composite":
            comparison = (result.get("parts") or {}).get("comparison") or {}
        else:
            comparison = result
        assert comparison.get("kind") == "comparison"
        assert comparison.get("location") == "青岛"
        assert comparison.get("years") == [2025]
        assert comparison.get("item_count") == 13
        items = comparison.get("items") or []
        weld_spot = next(item for item in items if item["item_name"] == "焊点")
        assert weld_spot["unit_price"] == "0.1300"
        assert weld_spot["year"] == 2025
    finally:
        db.close()
