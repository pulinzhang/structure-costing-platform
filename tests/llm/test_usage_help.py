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
        ("怎么导出月度核对？", "usage_help"),
        ("成品核价一览怎么导出 Excel？", "usage_help"),
        ("采购价格在哪？", "usage_help"),
        ("怎么导出批量零部件价格协议？", "usage_help"),
        ("我在进行成品核价计算时卡住了，怎么办？", "usage_help"),
        ("工程变更怎么上传？", "usage_help"),
        ("投产后改图换号走哪里？", "usage_help"),
        ("为什么新版本采购对象有 17 个", "usage_help"),
        ("变更单只有 5 条采购对象怎么这么多", "usage_help"),
        ("青岛 1 月成品价多少？", "analysis"),
        ("501006875AA 多少钱", "analysis"),
        ("2026年01月 T13J 项目总成核价有没有异常", "analysis"),
        ("2026年01月，冲压核价的异常", "analysis"),
        ("焊接成本计算异常", "analysis"),
        ("青岛当月待审核还有多少", "analysis"),
        ("总成核价怎么审核", "usage_help"),
        ("冲压零件价格计算页在哪", "usage_help"),
        ("怎么用简码问某个件的价？", "usage_help"),
        ("2856的价格多少？", "analysis"),
        ("2856最新价", "analysis"),
        ("2025年，T13J项目采购对象的费用是多少", "usage_help"),
        ("采购对象还有多少没确认外发", "analysis"),
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
        ("怎么导出月度核对", "export"),
        ("材料清单在哪上传", "bom_material"),
        ("引擎一直运行中怎么办", "faq_stuck"),
        ("我在进行成品核价计算时卡住了，怎么办？", "faq_calc_stuck"),
        ("采购对象在哪确认外发", "procurement"),
        ("2025年，T13J项目采购对象的费用是多少", "faq_procurement_fee"),
        ("采购价格在哪", "procurement_contract_report"),
        ("怎么导出批量零部件价格协议", "procurement_contract_report"),
        ("模具费怎么算进零件价", "die_gauge"),
        ("总成核价怎么审核", "audit"),
        ("冲压零件价格计算页在哪", "calc_run"),
        ("怎么用简码问某个件的价？", "part_lookup_how"),
        ("文件溯源在哪看", "file_trace"),
        ("牌号分类在哪维护", "masterdata"),
        ("工程变更怎么上传", "engineering-change"),
        ("投产后改图换号走哪里", "engineering-change"),
        ("此件不装怎么填", "engineering-change"),
        ("工程变更在哪", "engineering-change"),
        ("材料清单换号走哪里", "engineering-change"),
        ("生效月怎么算", "engineering_change_knowledge"),
        ("时间轴切点怎么理解", "engineering_change_knowledge"),
        ("为什么新版本采购对象有 17 个", "faq_ec_tree_vs_procurement"),
        ("变更单只有 5 条采购对象怎么这么多", "faq_ec_tree_vs_procurement"),
        ("设变从哪个月开始算新零件", "faq_ec_costing_effect_month"),
        ("这个月核价用旧号还是新号", "faq_ec_costing_effect_month"),
        ("旧零件过期了还能不能出协议", "faq_ec_costing_effect_month"),
        ("增加零件进采购对象后厂家要不要自己填", "faq_ec_costing_effect_month"),
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
        "faq_procurement_fee",
        "die_gauge",
        "file_trace",
        "masterdata",
        "assembly_cost",
        "procurement_contract_report",
        "audit",
        "calc_run",
        "part_lookup_how",
        "engineering-change",
        "engineering_change_knowledge",
        "faq_ec_costing_effect_month",
        "faq_ec_tree_vs_procurement",
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
