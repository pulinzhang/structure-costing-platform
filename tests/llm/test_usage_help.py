"""P1a：意图分流与帮助语料检索。"""

from __future__ import annotations

import pytest

from app.schemas.llm.analysis_query import AnalysisQuery, TimeRange
from app.services.llm.query.intent_router import detect_help_topic, detect_query_mode
from app.services.llm.usage.corpus import load_corpus_chunks
from app.services.llm.usage.manifest import retrieve_chunks
from app.services.llm.usage.runner import UsageHelpRunner


@pytest.mark.parametrize(
    ("question", "expected_mode"),
    [
        ("自动核价引擎怎么启动？", "usage_help"),
        ("看不到焊接工程菜单", "usage_help"),
        ("每月要维护哪些数据？", "usage_help"),
        ("怎么导出核对合册？", "usage_help"),
        ("成品核价一览怎么导出 Excel？", "usage_help"),
        ("采购价格在哪？", "usage_help"),
        ("怎么导出批量零部件价格协议？", "usage_help"),
        ("我在进行成品核价计算时卡住了，怎么办？", "usage_help"),
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
        ("我在进行成品核价计算时卡住了，怎么办？", "faq_calc_stuck"),
        ("采购对象在哪确认外发", "procurement"),
        ("采购价格在哪", "procurement_contract_report"),
        ("怎么导出批量零部件价格协议", "procurement_contract_report"),
        ("模具费怎么算进零件价", "die_gauge"),
        ("文件溯源在哪看", "file_trace"),
    ],
)
def test_detect_help_topic(question: str, expected_topic: str) -> None:
    assert detect_help_topic(question) == expected_topic


def test_load_corpus_has_p1a_sections() -> None:
    load_corpus_chunks.cache_clear()
    chunks = load_corpus_chunks()
    chunk_ids = {chunk.chunk_id for chunk in chunks}
    for required in (
        "start",
        "menu",
        "engine",
        "export",
        "faq_permission",
        "faq_stuck",
        "faq_calc_stuck",
        "monthly",
        "stamping",
        "welding",
        "procurement",
        "die_gauge",
        "file_trace",
        "assembly_cost",
        "procurement_contract_report",
    ):
        assert required in chunk_ids


def test_retrieve_engine_chunk() -> None:
    chunks = retrieve_chunks("自动核价引擎怎么启动？", primary_topic="engine", top_k=2)
    assert chunks
    assert chunks[0].chunk_id == "engine"


def test_usage_help_runner() -> None:
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


L0_CALC_STUCK_QUESTION = "我在进行成品核价计算时卡住了，怎么办？"


def test_query_parser_routes_l0_calc_stuck_to_usage_help() -> None:
    from unittest.mock import MagicMock

    from app.services.llm.query.query_parser import QueryParser

    parser = QueryParser()
    db = MagicMock()
    query = parser.parse(db, user_question=L0_CALC_STUCK_QUESTION)
    assert query.query_mode == "usage_help"
    assert query.subject == "usage_help"
    assert query.help_topic == "faq_calc_stuck"


def test_retrieve_l0_calc_stuck_chunk() -> None:
    load_corpus_chunks.cache_clear()
    chunks = retrieve_chunks(
        L0_CALC_STUCK_QUESTION,
        primary_topic="faq_calc_stuck",
        top_k=2,
    )
    assert chunks
    assert chunks[0].chunk_id == "faq_calc_stuck"
    assert "计算历史" in chunks[0].text
    assert "删除" in chunks[0].text
    assert "计算中" in chunks[0].text


def test_l0_calc_stuck_usage_help_fallback_markdown() -> None:
    """不依赖真实 LLM：语料命中后降级模板应包含删除计算历史指引。"""
    from app.services.llm.context.snapshot_builder import SnapshotBuilder
    from app.services.llm.generator import LlmReportGenerator
    from app.services.llm.query.query_parser import QueryParser

    load_corpus_chunks.cache_clear()
    parser = QueryParser()
    query = parser._parse_usage_help(L0_CALC_STUCK_QUESTION)
    assert query.query_mode == "usage_help"
    assert query.help_topic == "faq_calc_stuck"

    run = UsageHelpRunner().run(query)
    snapshot = SnapshotBuilder().build(query=query, run=run)
    markdown = LlmReportGenerator().render_fallback_markdown(
        snapshot=snapshot,
        error_hint="test",
    )
    assert "计算历史" in markdown
    assert "删除" in markdown
    assert "计算中" in markdown
    assert "成品核价计算" in markdown


PCR_HELP_QUESTION = "采购价格在哪导出协议？"


def test_detect_pcr_help_does_not_steal_procurement_object() -> None:
    assert detect_help_topic("采购对象在哪确认外发") == "procurement"
    assert detect_help_topic(PCR_HELP_QUESTION) == "procurement_contract_report"


def test_retrieve_pcr_help_chunk() -> None:
    load_corpus_chunks.cache_clear()
    chunks = retrieve_chunks(
        PCR_HELP_QUESTION,
        primary_topic="procurement_contract_report",
        top_k=2,
    )
    assert chunks
    assert chunks[0].chunk_id == "procurement_contract_report"
    assert "批量零部件价格协议" in chunks[0].text
    assert "不算价" in chunks[0].text
    assert "总成" in chunks[0].text
