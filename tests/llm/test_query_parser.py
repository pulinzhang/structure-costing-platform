# -*- coding: utf-8 -*-
"""QueryParser / 时间范围 / 趋势分析单测（不调真实 LLM、不改库）。"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from app.repositories.llm.cost_analysis_repository import L0MonthlyTotalRow
from app.services.llm.analysis.cost_trend import build_cost_trend
from app.services.llm.analysis.idempotency import (
    build_idempotency_key,
    question_fingerprint,
)
from app.services.llm.analysis.summary import build_summary
from app.services.llm.query.comparison_basis import default_comparison_basis
from app.services.llm.query.query_parser import QueryParser
from app.services.llm.query.time_range import DefaultScopeMonth, normalize_time_range


def test_normalize_range_explicit_months() -> None:
    tr = normalize_time_range(
        user_question="随便",
        default=DefaultScopeMonth(2026, 8),
        explicit_start="2026-01",
        explicit_end="2026-08",
    )
    assert tr.start == "2026-01"
    assert tr.end == "2026-08"
    assert tr.month_span() == 8


def test_normalize_range_from_question() -> None:
    tr = normalize_time_range(
        user_question="2026年1月到8月青岛采购成本怎么变化",
        default=DefaultScopeMonth(2026, 8),
    )
    assert tr.start == "2026-01"
    assert tr.end == "2026-08"


def test_normalize_recent_three_months() -> None:
    tr = normalize_time_range(
        user_question="近三个月成本怎么样",
        default=DefaultScopeMonth(2026, 8),
    )
    assert tr.start == "2026-06"
    assert tr.end == "2026-08"


def _mock_aligner(parser: QueryParser) -> None:
    parser._aligner._scope_repo.list_locations = MagicMock(  # noqa: SLF001
        return_value=["青岛"]
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(  # noqa: SLF001
        return_value=["T28"]
    )
    parser._aligner._scope_repo.list_bom_versions = MagicMock(  # noqa: SLF001
        return_value=["V1"]
    )
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(  # noqa: SLF001
        return_value=[]
    )


def test_query_parser_uses_llm_draft() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-01"},
            "filters": {"location": "青岛", "vehicle_model": "T28"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="青岛 2026年1月的采购成本总体怎么样？",
    )
    assert "summary" in query.analyses
    assert query.location() == "青岛"
    assert query.time_range.start == "2026-01"
    parser._extractor.extract.assert_called_once()  # noqa: SLF001


def test_query_parser_part_number_adds_drilldown() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2026-08", "end": "2026-08"},
            "filters": {},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="501006875AA 为什么这么贵？",
    )
    assert "drilldown" in query.analyses
    assert query.part_number() == "501006875AA"


def test_query_parser_price_detail_skips_dashboard_summary() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="2025-01 青岛 9144的价格详情",
    )
    assert query.analyses == ["drilldown"]
    assert "summary" not in query.analyses
    assert query.subject == "l0"
    assert query.part_number() == "9144"
    assert query.location() == "青岛"


def test_price_detail_l0_action_only() -> None:
    from app.services.llm.action_builder import ActionBuilder
    from app.services.llm.analysis.runner import AnalysisRunResult

    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="2025-01 青岛 9144的价格详情",
    )
    run = AnalysisRunResult(
        evidence={
            "part_lookup": {
                "l0_rows": 1,
                "stamping_cost_rows": 0,
                "stamping_process_rows": 0,
            }
        }
    )
    actions = ActionBuilder().build(query=query, run=run)
    assert len(actions) == 1
    assert actions[0].action_id == "open_l0_assembly_cost"


def test_query_parser_rule_fallback_when_llm_fails() -> None:
    from app.services.llm.client import LlmClientError

    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        side_effect=LlmClientError("no key")
    )

    query = parser.parse(
        db,
        user_question="近三个月青岛成本怎么样",
    )
    assert query.location() == "青岛"
    assert "summary" in query.analyses
    assert "trend" in query.analyses


def test_build_summary_and_trend() -> None:
    rows = [
        L0MonthlyTotalRow(
            year=2026,
            month=1,
            location="青岛",
            l0_count=10,
            ok_count=9,
            partial_count=1,
            grand_total_sum=Decimal("1000"),
            total_amount_sum=Decimal("900"),
            indirect_amount_sum=Decimal("100"),
            stamping_amount_sum=Decimal("500"),
            purchased_amount_sum=Decimal("200"),
            bundle_amount_sum=Decimal("50"),
            welding_amount_sum=Decimal("150"),
            welding_other_amount_sum=Decimal("0"),
        ),
        L0MonthlyTotalRow(
            year=2026,
            month=2,
            location="青岛",
            l0_count=10,
            ok_count=10,
            partial_count=0,
            grand_total_sum=Decimal("1100"),
            total_amount_sum=Decimal("990"),
            indirect_amount_sum=Decimal("110"),
            stamping_amount_sum=Decimal("550"),
            purchased_amount_sum=Decimal("200"),
            bundle_amount_sum=Decimal("50"),
            welding_amount_sum=Decimal("150"),
            welding_other_amount_sum=Decimal("0"),
        ),
    ]
    summary = build_summary(rows)
    assert summary["l0_count"] == 20
    assert summary["grand_total_sum"] == "2100.0000"

    trend = build_cost_trend(rows, basis=default_comparison_basis())
    assert trend["kind"] == "trend"
    assert trend["cumulative_rate"] == "0.1000"
    assert len(trend["points"]) == 2


def test_query_parser_winning_thickness_not_base_price() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="青岛基地，2025年01月，中标厚度价的情况。",
    )
    assert query.subject == "winning_thickness"
    assert query.subject != "steel_base_price"


def test_query_parser_scrap_price_not_cost_total() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="青岛基地，2025年01月，废料销售价的情况。",
    )
    assert query.subject == "scrap_price"
    assert query.subject not in ("cost_total", "l0")


def test_query_parser_stamping_process_maps_to_parts_list() -> None:
    from app.services.llm.action_builder import ActionBuilder
    from app.services.llm.analysis.runner import AnalysisRunResult

    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {
                "location": "青岛",
                "vehicle_model": "T28",
                "bom_version": "V1",
            },
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="青岛 T28 V1 冲压工艺情况怎么样？",
    )
    assert query.subject == "stamping_process"
    assert query.location() == "青岛"
    assert query.vehicle_model() == "T28"
    assert "summary" in query.analyses
    assert "drivers" in query.analyses
    assert "trend" not in query.analyses

    action = ActionBuilder().build(query=query, run=AnalysisRunResult())[0]
    assert action.action_id == "open_stamping_parts"
    assert action.target.startswith("#/stamping-parts?")
    assert "location=%E9%9D%92%E5%B2%9B" in action.target
    assert "vehicle_model=T28" in action.target
    assert "version=V1" in action.target


def test_build_stamping_process_summary() -> None:
    from decimal import Decimal

    from app.repositories.llm.stamping_process_analysis_repository import (
        StampingProcessPartRow,
    )
    from app.services.llm.analysis.stamping_process_summary import (
        build_stamping_process_summary,
    )

    rows = [
        StampingProcessPartRow(
            part_id=1,
            part_number="P1",
            part_name="件1",
            location="青岛",
            vehicle_model="T28",
            version="V1",
            stamping_supplier="供应商A",
            material="DC04",
            thickness=Decimal("0.8"),
            is_tailor_welded=False,
            process_count=3,
            max_tonnage=800,
        ),
        StampingProcessPartRow(
            part_id=2,
            part_number="P2",
            part_name="件2",
            location="青岛",
            vehicle_model="T28",
            version="V1",
            stamping_supplier="供应商A",
            material=None,
            thickness=None,
            is_tailor_welded=True,
            process_count=0,
            max_tonnage=None,
        ),
    ]
    summary = build_stamping_process_summary(rows)
    assert summary["part_count"] == 2
    assert summary["process_count"] == 3
    assert summary["tailor_welded_count"] == 1
    assert summary["parts_without_process"] == 1


def test_query_parser_stamping_report_maps_to_part_cost() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="2025年01月，青岛基地冲压件成本报告。",
    )
    assert query.location() == "青岛"
    assert query.time_range.start == "2025-01"
    assert query.subject == "stamping_part"
    assert "summary" in query.analyses
    assert "drivers" in query.analyses


def test_build_stamping_summary() -> None:
    from app.repositories.llm.stamping_cost_analysis_repository import (
        StampingPartPeriodRow,
    )
    from app.services.llm.analysis.summary import build_stamping_summary

    rows = [
        StampingPartPeriodRow(
            year=2025,
            month=1,
            part_number="P1",
            part_name="件1",
            unit_cost=Decimal("10"),
            material_net_per_part=Decimal("6"),
            process_fee_amount=Decimal("4"),
            calc_status="success",
            stamping_supplier="供应商A",
        ),
        StampingPartPeriodRow(
            year=2025,
            month=1,
            part_number="P2",
            part_name="件2",
            unit_cost=Decimal("20"),
            material_net_per_part=None,
            process_fee_amount=None,
            calc_status="failed",
            stamping_supplier="供应商B",
        ),
    ]
    summary = build_stamping_summary(rows)
    assert summary["part_count"] == 2
    assert summary["success_count"] == 1
    assert summary["failed_count"] == 1
    assert summary["unit_cost_sum"] == "30.0000"


def test_query_parser_l0_finished_product_cost_report() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="2025年01月，青岛基地成品成本报告。",
    )
    assert query.location() == "青岛"
    assert query.subject == "l0"
    assert "summary" in query.analyses
    assert "drivers" in query.analyses

    from app.services.llm.action_builder import ActionBuilder
    from app.services.llm.analysis.runner import AnalysisRunResult

    action = ActionBuilder().build(query=query, run=AnalysisRunResult())[0]
    assert action.action_id == "open_l0_assembly_cost"
    assert action.target.startswith("#/l0-assembly-cost?")


def test_query_parser_thickness_policy_question() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="2025年01月，厚度加减价的情况？",
    )
    assert query.subject == "steel_price_policy"
    assert query.filters.get("policy_type") == "THICKNESS"
    assert query.time_range.start == "2025-01"
    assert "summary" in query.analyses
    assert "drivers" in query.analyses

    from app.services.llm.action_builder import ActionBuilder
    from app.services.llm.analysis.runner import AnalysisRunResult

    action = ActionBuilder().build(query=query, run=AnalysisRunResult())[0]
    assert action.action_id == "open_steel_price_policy"
    assert action.target.startswith("#/steel-price-policy-download?")
    assert "year=2025" in action.target
    assert "month=1" in action.target


def test_query_parser_base_price_question() -> None:
    from unittest.mock import MagicMock

    from app.services.llm.action_builder import ActionBuilder
    from app.services.llm.analysis.runner import AnalysisRunResult
    from app.services.llm.query.query_parser import QueryParser

    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])  # noqa: SLF001
    parser._extractor.extract = MagicMock(  # noqa: SLF001
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="2025年01月青岛基准价怎么样？",
    )
    assert query.subject == "steel_base_price"
    assert query.time_range.start == "2025-01"
    assert "summary" in query.analyses
    assert "drivers" in query.analyses

    action = ActionBuilder().build(query=query, run=AnalysisRunResult())[0]
    assert action.action_id == "open_steel_base_price"
    assert action.target.startswith("#/base-price-download?")
    assert "location=%E9%9D%92%E5%B2%9B%E5%9F%BA%E5%9C%B0" in action.target


def test_idempotency_fingerprint_stable() -> None:
    assert question_fingerprint("A  B") == question_fingerprint("a b")
    key = build_idempotency_key(
        report_type="auto",
        audience="buyer",
        location="青岛",
        year=2026,
        month=1,
        vehicle_model="T28",
        bom_version="V1",
        user_question="测试",
        user_id=1,
    )
    assert "q:" in key
