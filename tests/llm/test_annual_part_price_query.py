# -*- coding: utf-8 -*-
"""年度零件价 / 一口价 问句解析与取数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.query_parser import QueryParser


def test_query_parser_annual_part_price_subject() -> None:
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
        user_question="今年与去年，青岛基地，年度零件价，比较。",
    )
    assert query.subject == "annual_part_price"
    assert query.location() == "青岛"
    assert "comparison" in query.analyses


def test_query_parser_yikoujia_alias() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(  # noqa: SLF001
        return_value=["青岛"]
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(  # noqa: SLF001
        return_value=[]
    )
    parser._aligner._scope_repo.list_bom_versions = MagicMock(  # noqa: SLF001
        return_value=[]
    )
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(  # noqa: SLF001
        return_value=["501004437AA"]
    )
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-08"},
            "filters": {"location": "青岛", "part_number": "4437"},
            "compare_locations": [],
        }
    )

    query = parser.parse(db, user_question="青岛，4437，一口价多少")
    assert query.subject == "annual_part_price"
    assert query.part_number() == "501004437AA"
    assert "drilldown" in query.analyses


@pytest.mark.integration
def test_annual_part_price_qingdao_yoy() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        parser = QueryParser()
        parser._extractor.extract = MagicMock(  # noqa: SLF001
            return_value={
                "time_range": {"start": "2025-01", "end": "2025-12"},
                "filters": {"location": "青岛基地"},
                "compare_locations": [],
            }
        )
        query = parser.parse(
            db,
            user_question="今年与去年，青岛基地，年度零件价，比较。",
        )
        assert query.subject == "annual_part_price"

        run = AnalysisRunner().run(db, query)
        assert run.has_data is True
        assert run.summary is not None
        assert run.summary["row_count"] == 45
        assert run.summary["years"] == [2025]

        result = run.result
        if result.get("kind") == "composite":
            comparison = (result.get("parts") or {}).get("comparison") or {}
        else:
            comparison = result
        assert comparison.get("location") == "青岛"
        assert comparison.get("part_count") == 45
    finally:
        db.close()


@pytest.mark.integration
def test_annual_part_price_yikoujia_drilldown() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(db, user_question="青岛，4437，一口价多少")
        assert query.subject == "annual_part_price"

        run = AnalysisRunner().run(db, query)
        assert run.has_data is True

        result = run.result
        if result.get("kind") == "composite":
            drill = (result.get("parts") or {}).get("drilldown") or {}
        else:
            drill = result
        assert drill.get("found") is True
        assert drill.get("part_number") == "501004437AA"
        assert drill.get("unit_price") == "2.1300"
    finally:
        db.close()
