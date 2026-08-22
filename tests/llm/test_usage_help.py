"""P1a：意图分流与帮助语料检索。"""

from __future__ import annotations

import pytest

from app.schemas.llm.analysis_query import AnalysisQuery, TimeRange
from app.services.llm.action_builder import ActionBuilder
from app.services.llm.query.intent_router import detect_help_topic, detect_query_mode
from app.services.llm.usage.manifest import retrieve_chunks
from app.services.llm.usage.runner import UsageHelpRunner
from app.services.llm.usage.corpus import load_corpus_chunks


@pytest.mark.parametrize(
    ("question", "expected_mode"),
    [
        ("自动核价引擎怎么启动？", "usage_help"),
        ("看不到焊接工程菜单", "usage_help"),
        ("每月要维护哪些数据？", "usage_help"),
        ("怎么导出核对合册？", "usage_help"),
        ("青岛 1 月成品价多少？", "analysis"),
        ("501006875AA 多少钱", "analysis"),
    ],
)
def test_detect_query_mode(question: str, expected_mode: str) -> None:
    assert detect_query_mode(question) == expected_mode


@pytest.mark.parametrize(
    ("question", "expected_topic"),
    [
        ("自动核价引擎怎么启动？", "engine"),
        ("看不到焊接工程菜单", "faq_permission"),
        ("每月要维护哪些数据？", "monthly"),
        ("怎么导出 Excel 合册", "export"),
        ("材料清单在哪上传", "bom_material"),
        ("引擎一直运行中怎么办", "faq_stuck"),
    ],
)
def test_detect_help_topic(question: str, expected_topic: str) -> None:
    assert detect_help_topic(question) == expected_topic


def test_load_corpus_has_p1a_sections() -> None:
    chunks = load_corpus_chunks()
    chunk_ids = {chunk.chunk_id for chunk in chunks}
    for required in (
        "start",
        "menu",
        "engine",
        "export",
        "faq_permission",
        "faq_stuck",
        "monthly",
    ):
        assert required in chunk_ids


def test_retrieve_engine_chunk() -> None:
    chunks = retrieve_chunks("自动核价引擎怎么启动？", primary_topic="engine", top_k=2)
    assert chunks
    assert chunks[0].chunk_id == "engine"


def test_usage_help_runner_and_actions() -> None:
    query = AnalysisQuery(
        time_range=TimeRange(start="2026-01", end="2026-01"),
        user_question="自动核价引擎怎么启动？",
        query_mode="usage_help",
        help_topic="engine",
        subject="usage_help",
    )
    run = UsageHelpRunner().run(query)
    assert run.has_data
    assert run.result.get("kind") == "usage_help"
    assert run.evidence.get("corpus_chunks")

    actions = ActionBuilder().build(query=query, run=run)
    targets = [action.target for action in actions]
    assert "#/costing" in targets
    assert any("/helper/help.html#engine" in target for target in targets)
