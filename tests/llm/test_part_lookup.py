"""单件跨域检索 runner 集成（真实库）。"""

from __future__ import annotations

import pytest

from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.parser.pipeline import QueryParser


@pytest.mark.integration
def test_part_lookup_finds_stamping_when_l0_missing() -> None:
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        parser = QueryParser()
        query = parser.parse(db, user_question="501008898AA，存在吗？")
        assert query.subject == "part"
        assert query.part_number() == "501008898AA"

        run = AnalysisRunner().run(db, query)
        if not run.has_data:
            pytest.skip(run.data_message or "库中无 501008898AA")
        assert "冲压" in run.data_message
        assert run.summary is not None
        assert run.summary.get("in_stamping_process") is True
        assert run.summary.get("exists_any") is True

        result = run.result
        if result.get("kind") == "composite":
            existence = (result.get("parts") or {}).get("existence") or {}
        else:
            existence = result
        assert existence.get("kind") == "part_existence"
        assert existence.get("exists_any") is True
        assert existence["stamping_process"]["found"] is True
        assert existence["stamping_process"]["part_number"] == "501008898AA"
    finally:
        db.close()
