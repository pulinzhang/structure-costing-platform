"""引擎就绪问句：解析与取数对齐 CostingEngineService.get_ready。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.services.llm.context.snapshot_builder import SnapshotBuilder
from app.services.llm.engine_readiness import EngineReadinessRunner
from app.services.llm.engine_readiness.runner import render_engine_readiness_markdown
from app.services.llm.generator import LlmReportGenerator
from app.services.llm.query.intent_router import detect_query_mode
from app.services.llm.query.query_parser import QueryParser


def test_detect_engine_readiness_mode() -> None:
    assert detect_query_mode("青岛 2026年02月还差什么数据才能自动核价？") == "engine_readiness"
    assert detect_query_mode("自动核价引擎怎么用？") == "usage_help"


def test_parse_engine_readiness_qingdao_feb_2026() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛", "芜湖"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛", "芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["D/00"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-02", "end": "2026-02"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="青岛 2026年02月还差什么数据才能核算？",
    )
    assert query.query_mode == "engine_readiness"
    assert query.subject == "engine_readiness"
    assert query.time_range.start == "2026-02"
    assert query.location() == "青岛"


@pytest.mark.integration
def test_engine_readiness_qingdao_2026_02_lists_hard_gates() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(
            db,
            user_question="青岛 2026年02月还差什么数据才能核算？",
        )
        assert query.query_mode == "engine_readiness"

        run = EngineReadinessRunner().run(db, query)
        assert run.has_data is True
        assert run.result.get("kind") == "engine_readiness"
        assert run.summary is not None
        assert run.summary.get("location") == "青岛"
        assert run.summary.get("year") == 2026
        assert run.summary.get("month") == 2

        gates = run.result.get("gates") or []
        bom_gate = next(g for g in gates if g["code"] == "bom_snapshot")
        assert bom_gate["ok"] is True

        hard_fails = [g for g in gates if g.get("hard_stop")]
        assert {g["code"] for g in hard_fails} >= {
            "welding_unit_price",
        }
        pkg = next((g for g in gates if g["code"] == "packaging_transport"), None)
        if pkg is not None and not pkg.get("ok"):
            assert pkg.get("hard_stop") is False
            assert pkg.get("soft_hint") is True

        snapshot = SnapshotBuilder().build(query=query, run=run)
        markdown = LlmReportGenerator().render_fallback_markdown(
            snapshot=snapshot,
            error_hint="test",
        )
        assert "材料清单" in markdown or "BOM" in markdown
        assert "已就绪" in markdown
        assert "焊接单价" in markdown
        assert "跨年复用" in markdown
        assert "不要求每年重传" in markdown
        hard_section = (
            markdown.split("### 还缺")[1].split("###")[0] if "### 还缺" in markdown else ""
        )
        assert "材料清单" not in hard_section
        assert "包装运输" not in hard_section
    finally:
        db.close()


@pytest.mark.integration
def test_render_engine_readiness_markdown_matches_service() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(
            db,
            user_question="青岛，2026年02月，还差那些数据，我才可以自动核价？",
        )
        run = EngineReadinessRunner().run(db, query)
        from app.schemas.vo.costing_engine_vo import CostingEngineReadyVO

        ready = CostingEngineReadyVO.model_validate(run.evidence["engine_ready"])
        text = render_engine_readiness_markdown(
            user_question=query.user_question,
            ready=ready,
        )
        assert "2026年02月" in text
        assert "跨年复用" in text
        if not ready.can_start:
            assert "还缺" in text
    finally:
        db.close()
