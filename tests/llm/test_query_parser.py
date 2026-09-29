"""QueryParser / 时间范围 / 趋势分析单测（不调真实 LLM、不改库）。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.repositories.llm.cost_analysis.rows import (
    L0MonthlyTotalRow,
    L0PartPeriodRow,
)
from app.services.llm.analysis.shared.cost_trend import build_cost_trend
from app.services.llm.analysis.shared.idempotency import (
    build_idempotency_key,
    question_fingerprint,
)
from app.services.llm.analysis.shared.summary import build_summary
from app.services.llm.comparison_basis import default_comparison_basis
from app.services.llm.query.parser.pipeline import QueryParser
from app.services.llm.query.parser.subjects import resolve_subject
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
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V1"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])


def test_query_parser_uses_llm_draft() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
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
    parser._extractor.extract.assert_called_once()


def test_query_parser_part_number_adds_drilldown() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
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
    parser._extractor.extract = MagicMock(
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


def test_query_parser_latest_costing_uses_table_month() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {},
            "compare_locations": [],
        }
    )
    parser._cost_repo.query_latest_card_scope = MagicMock(
        return_value=SimpleNamespace(
            year=2026,
            month=1,
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            part_number="551002856AA",
            is_tree_root=False,
            object_kind="l1_stamping",
            root_part_number="551002784AA",
        )
    )
    query = parser.parse(
        db,
        user_question="2856零件，最近一次核价是多少钱？",
    )
    assert query.part_number() == "2856"
    assert query.analyses == ["drilldown"]
    assert query.subject == "l0"
    assert query.time_range.start == "2026-01"
    assert query.time_range.end == "2026-01"
    assert query.location() == "芜湖"
    assert query.vehicle_model() == "T13J"
    assert query.parser_data_message is not None
    assert "2026年01月" in query.parser_data_message


def test_query_parser_operator_short_code_price() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {},
            "compare_locations": [],
        }
    )
    parser._cost_repo.query_latest_card_scope = MagicMock(
        return_value=SimpleNamespace(
            year=2026,
            month=1,
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            part_number="551002856AA",
            is_tree_root=False,
            object_kind="l1_stamping",
            root_part_number="551002784AA",
        )
    )
    query = parser.parse(db, user_question="2856的价格多少？")
    assert query.part_number() == "2856"
    assert query.analyses == ["drilldown"]
    assert query.subject == "l0"
    assert query.time_range.start == "2026-01"
    assert query.time_range.end == "2026-01"


def test_query_parser_operator_latest_price_phrase() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {},
            "compare_locations": [],
        }
    )
    parser._cost_repo.query_latest_card_scope = MagicMock(
        return_value=SimpleNamespace(
            year=2026,
            month=1,
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            part_number="551002856AA",
            is_tree_root=False,
            object_kind="l1_stamping",
            root_part_number="551002784AA",
        )
    )
    query = parser.parse(db, user_question="2856最新价")
    assert query.analyses == ["drilldown"]
    assert query.time_range.start == "2026-01"


def test_normalize_yoy_range() -> None:
    tr = normalize_time_range(
        user_question="今年与去年，青岛基地，年度零件价，比较。",
        default=DefaultScopeMonth(2026, 8),
    )
    assert tr.start == "2025-01"
    assert tr.end == "2026-08"


def test_query_parser_level4_blind_question_forces_safe_analyses() -> None:
    from app.services.llm.client.openai_compatible import LlmClientError

    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(side_effect=LlmClientError("no key"))

    query = parser.parse(db, user_question="总体怎么样")
    assert query.analyses == ["summary", "risk"]
    assert query.filters == {}
    assert query.parser_fallback_level == 4


def test_query_parser_rule_fallback_when_llm_fails() -> None:
    from app.common.timezone import now
    from app.services.llm._money import month_key, shift_month
    from app.services.llm.client.openai_compatible import LlmClientError

    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(side_effect=LlmClientError("no key"))

    query = parser.parse(
        db,
        user_question="近三个月青岛成本怎么样",
    )
    assert query.location() == "青岛"
    assert "trend" in query.analyses
    assert query.parser_fallback_level == 4
    current = now()
    start_year, start_month = shift_month(current.year, current.month, -2)
    assert query.time_range.start == month_key(start_year, start_month)


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
    assert summary["l0_count"] == 10
    assert summary["grand_total_sum"] == "2100.00"

    trend = build_cost_trend(rows, basis=default_comparison_basis())
    assert trend["kind"] == "trend"
    assert trend["cumulative_rate"] == "0.10"
    assert len(trend["points"]) == 2

    single_month_trend = build_cost_trend(
        rows[:1],
        basis=default_comparison_basis(),
        single_month=True,
    )
    assert single_month_trend["cumulative_rate"] is None


def test_build_summary_multi_month_deduplicates_part_count() -> None:
    monthly = [
        L0MonthlyTotalRow(
            year=2025,
            month=1,
            location="青岛",
            l0_count=27,
            ok_count=27,
            partial_count=0,
            grand_total_sum=Decimal("100"),
            total_amount_sum=Decimal("90"),
            indirect_amount_sum=Decimal("10"),
            stamping_amount_sum=Decimal("50"),
            purchased_amount_sum=Decimal("20"),
            bundle_amount_sum=Decimal("5"),
            welding_amount_sum=Decimal("15"),
            welding_other_amount_sum=Decimal("0"),
        ),
        L0MonthlyTotalRow(
            year=2025,
            month=3,
            location="青岛",
            l0_count=27,
            ok_count=27,
            partial_count=0,
            grand_total_sum=Decimal("110"),
            total_amount_sum=Decimal("99"),
            indirect_amount_sum=Decimal("11"),
            stamping_amount_sum=Decimal("55"),
            purchased_amount_sum=Decimal("20"),
            bundle_amount_sum=Decimal("5"),
            welding_amount_sum=Decimal("15"),
            welding_other_amount_sum=Decimal("0"),
        ),
    ]
    part_rows = [
        L0PartPeriodRow(
            year=2025,
            month=month,
            part_number=f"50100687{i}AA",
            part_name="件",
            grand_total=Decimal("1"),
            total_amount=Decimal("1"),
            calc_status="ok",
            missing_leaf_count=0,
            calc_message=None,
            stamping_amount=Decimal("0"),
            purchased_amount=Decimal("0"),
            bundle_amount=Decimal("0"),
            welding_amount=Decimal("0"),
            welding_other_fee=Decimal("0"),
            indirect_amount=Decimal("0"),
            bom_version="D/00",
        )
        for month in (1, 3)
        for i in range(3)
    ]
    summary = build_summary(monthly, part_rows=part_rows)
    assert summary["l0_count"] == 3
    assert summary["partial_count"] == 0
    assert summary["grand_total_sum"] == "210.00"


def test_query_parser_winning_thickness_not_base_price() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
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
    parser._extractor.extract = MagicMock(
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
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
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

    from app.services.llm.menu_catalog import build_list_params

    params = build_list_params(query)
    assert params.get("location") == "青岛"
    assert params.get("vehicle_model") == "T28"
    assert params.get("version") == "V1"


def test_build_stamping_process_summary() -> None:
    from decimal import Decimal

    from app.repositories.llm.stamping_process_analysis_repository import (
        StampingProcessPartRow,
    )
    from app.services.llm.analysis.stamping.process import (
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
    parser._extractor.extract = MagicMock(
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
    from app.services.llm.analysis.shared.summary import build_stamping_summary

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
    assert summary["unit_cost_sum"] == "30.00"


def test_query_parser_l0_finished_product_cost_report() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
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


def test_query_parser_thickness_policy_question() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._extractor.extract = MagicMock(
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

    from app.services.llm.menu_catalog import build_list_params

    params = build_list_params(query)
    assert params.get("year") == "2025"
    assert params.get("month") == "1"


def test_query_parser_base_price_question() -> None:
    from unittest.mock import MagicMock

    from app.services.llm.menu_catalog import build_list_params
    from app.services.llm.query.parser.pipeline import QueryParser

    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛"}
    )
    parser._extractor.extract = MagicMock(
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

    params = build_list_params(query)
    assert params.get("location") == "青岛"
    assert params.get("year") == "2025"
    assert params.get("month") == "1"


def test_idempotency_fingerprint_stable() -> None:
    assert question_fingerprint("A  B") == question_fingerprint("a b")
    key = build_idempotency_key(
        report_type="auto",
        audience="buyer",
        user_question="测试",
        user_id=1,
        time_range_start="2026-01",
        time_range_end="2026-01",
        filters={"location": "青岛", "vehicle_model": "T28", "bom_version": "V1"},
    )
    assert "q:" in key


def test_normalize_year_first_n_months() -> None:
    tr = normalize_time_range(
        user_question="2025年前6个月核算里最大的风险是什么",
        default=DefaultScopeMonth(2026, 8),
    )
    assert tr.start == "2025-01"
    assert tr.end == "2025-06"


def test_build_l0_mom_anomalies_ranks_jump() -> None:
    from decimal import Decimal

    from app.repositories.llm.cost_analysis.rows import L0PartPeriodRow
    from app.services.llm.analysis.shared.cost_driver import build_l0_mom_anomalies

    rows = [
        L0PartPeriodRow(
            year=2025,
            month=1,
            part_number="P001",
            part_name="件A",
            grand_total=Decimal("100"),
            total_amount=Decimal("90"),
            calc_status="ok",
            missing_leaf_count=0,
            calc_message=None,
            stamping_amount=Decimal("50"),
            purchased_amount=Decimal("20"),
            bundle_amount=Decimal("0"),
            welding_amount=Decimal("10"),
            welding_other_fee=Decimal("0"),
            indirect_amount=Decimal("10"),
            bom_version="V1",
        ),
        L0PartPeriodRow(
            year=2025,
            month=2,
            part_number="P001",
            part_name="件A",
            grand_total=Decimal("200"),
            total_amount=Decimal("180"),
            calc_status="ok",
            missing_leaf_count=0,
            calc_message=None,
            stamping_amount=Decimal("100"),
            purchased_amount=Decimal("40"),
            bundle_amount=Decimal("0"),
            welding_amount=Decimal("20"),
            welding_other_fee=Decimal("0"),
            indirect_amount=Decimal("20"),
            bom_version="V1",
        ),
    ]
    result = build_l0_mom_anomalies(rows, top_n=5)
    assert result["kind"] == "mom_anomalies"
    assert len(result["items"]) == 1
    top = result["items"][0]
    assert top["part_number"] == "P001"
    assert top["month"] == "2025-02"
    assert top["change"] == "90.00"


def _assembly_row(
    *,
    month: int,
    part_number: str = "P001",
    total_amount: Decimal,
    calc_status: str = "ok",
    year: int = 2026,
) -> L0PartPeriodRow:
    return L0PartPeriodRow(
        year=year,
        month=month,
        part_number=part_number,
        part_name="件A",
        grand_total=total_amount,
        total_amount=total_amount,
        calc_status=calc_status,
        missing_leaf_count=0,
        calc_message=None,
        stamping_amount=Decimal("0"),
        purchased_amount=Decimal("0"),
        bundle_amount=Decimal("0"),
        welding_amount=Decimal("0"),
        welding_other_fee=Decimal("0"),
        indirect_amount=Decimal("0"),
        bom_version="V1",
        should_cost=total_amount,
    )


def test_build_l0_mom_anomalies_requires_ten_percent() -> None:
    from app.services.llm.analysis.shared.cost_driver import build_l0_mom_anomalies

    under = [
        _assembly_row(month=12, total_amount=Decimal("100"), year=2025),
        _assembly_row(month=1, total_amount=Decimal("109"), year=2026),
    ]
    over = [
        _assembly_row(month=12, total_amount=Decimal("100"), year=2025),
        _assembly_row(month=1, total_amount=Decimal("110"), year=2026),
    ]
    under_result = build_l0_mom_anomalies(under, focus_month="2026-01")
    over_result = build_l0_mom_anomalies(over, focus_month="2026-01")
    assert under_result["items"] == []
    assert len(over_result["items"]) == 1
    assert over_result["items"][0]["change_rate"] == "0.10"


def test_build_risks_zero_unit_price() -> None:
    from app.services.llm.analysis.shared.anomaly import build_risks

    rows = [
        _assembly_row(month=1, part_number="ZERO1", total_amount=Decimal("0")),
        _assembly_row(month=1, part_number="OK1", total_amount=Decimal("12.5")),
    ]
    result = build_risks(rows)
    zero = next(item for item in result["risks"] if item["risk_type"] == "zero_unit_price")
    assert result["zero_unit_price_count"] == 1
    assert zero["sample_part_numbers"] == ["ZERO1"]


def test_query_parser_assembly_cost_anomaly_routes_to_l0() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T13J", "T28"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-01"},
            "filters": {"vehicle_model": "T13J"},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="2026年01月 T13J 项目总成核价有没有异常",
    )
    assert query.query_mode == "analysis"
    assert query.subject == "l0"
    assert query.vehicle_model() == "T13J"
    assert query.time_range.start == "2026-01"
    assert query.time_range.end == "2026-01"
    assert "risk" in query.analyses
    assert "drivers" in query.analyses


def test_query_parser_stamping_cost_anomaly_routes_to_part_cost() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-01"},
            "filters": {},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="2026年01月，冲压核价的异常",
    )
    assert query.query_mode == "analysis"
    assert query.subject == "stamping_part"
    assert "risk" in query.analyses
    assert "drivers" in query.analyses


def test_build_stamping_mom_anomalies_requires_ten_percent() -> None:
    from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
    from app.services.llm.analysis.shared.cost_driver import build_stamping_mom_anomalies

    def row(month: int, year: int, unit_cost: Decimal) -> StampingPartPeriodRow:
        return StampingPartPeriodRow(
            year=year,
            month=month,
            part_number="S001",
            part_name="冲压件",
            unit_cost=unit_cost,
            material_net_per_part=None,
            process_fee_amount=None,
            calc_status="success",
            stamping_supplier="供应商A",
        )

    under = [row(12, 2025, Decimal("100")), row(1, 2026, Decimal("109"))]
    over = [row(12, 2025, Decimal("100")), row(1, 2026, Decimal("110"))]
    assert build_stamping_mom_anomalies(under, focus_month="2026-01")["items"] == []
    over_result = build_stamping_mom_anomalies(over, focus_month="2026-01")
    assert len(over_result["items"]) == 1
    assert over_result["items"][0]["change_rate"] == "0.10"


def test_query_parser_max_risk_question() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-06"},
            "filters": {"location": "青岛"},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="2025年前6个月，核算里最大的风险是什么？",
    )
    assert query.time_range.start == "2025-01"
    assert query.time_range.end == "2025-06"
    assert "risk" in query.analyses
    assert "drivers" in query.analyses
    assert "trend" in query.analyses


def test_normalize_year_only_base_price() -> None:
    tr = normalize_time_range(
        user_question="2025年基准价有无异常",
        default=DefaultScopeMonth(2026, 8),
    )
    assert tr.start == "2025-01"
    assert tr.end == "2025-12"


def test_build_base_price_mom_anomalies() -> None:
    from decimal import Decimal

    from app.repositories.llm.base_price_analysis_repository import BasePricePeriodRow
    from app.services.llm.analysis.steel.base_price import build_base_price_mom_anomalies

    rows = [
        BasePricePeriodRow(
            year=2025,
            month=1,
            location="青岛基地",
            steel_mill="宝钢",
            steel_mill_id=3,
            category_name="冷轧",
            grade="DC04",
            spec="1.0",
            base_price=Decimal("4000"),
            processing_fee=Decimal("100"),
        ),
        BasePricePeriodRow(
            year=2025,
            month=2,
            location="青岛基地",
            steel_mill="宝钢",
            steel_mill_id=3,
            category_name="冷轧",
            grade="DC04",
            spec="1.0",
            base_price=Decimal("5000"),
            processing_fee=Decimal("100"),
        ),
    ]
    result = build_base_price_mom_anomalies(rows, top_n=5)
    assert result["kind"] == "base_price_anomalies"
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["month"] == "2025-02"
    assert item["steel_mill"] == "宝钢"
    assert item["change"] == "1000.00"


def test_query_parser_base_price_anomaly() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-12"},
            "filters": {"location": "青岛"},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="2025年基准价分析一下，有没有传错的？",
    )
    assert query.subject == "steel_base_price"
    assert query.time_range.start == "2025-01"
    assert query.time_range.end == "2025-12"
    assert "trend" in query.analyses
    assert "drivers" in query.analyses


def test_query_parser_zhongbiao_price_alias() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-12"},
            "filters": {"location": "青岛"},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="2025年中标价有没有异常，是不是传错了？",
    )
    assert query.subject == "steel_base_price"
    assert query.time_range.start == "2025-01"
    assert query.time_range.end == "2025-12"
    assert "trend" in query.analyses


def test_winning_thickness_not_confused_with_zhongbiao_price() -> None:
    assert (
        resolve_subject(
            question="中标厚度价格一览表怎么样",
            analyses=["summary"],
            filters={},
        )
        == "winning_thickness"
    )
    assert (
        resolve_subject(
            question="2025年中标价波动大吗",
            analyses=["summary"],
            filters={},
        )
        == "steel_base_price"
    )


def test_build_policy_mom_anomalies() -> None:
    from decimal import Decimal

    from app.repositories.llm.policy_analysis_repository import PolicyLadderRow
    from app.services.llm.analysis.steel.policy import build_policy_mom_anomalies

    rows = [
        PolicyLadderRow(
            policy_id=1,
            year=2025,
            month=1,
            steel_mill="宝钢",
            steel_mill_id=3,
            category_name="冷轧",
            policy_type="THICKNESS",
            grade_value="DC04",
            base_thickness=Decimal("1.0"),
            price_adjustment=50,
            thick_min=Decimal("0.8"),
            thick_max=Decimal("1.2"),
            is_base=0,
            sheet_name="宝钢",
        ),
        PolicyLadderRow(
            policy_id=2,
            year=2025,
            month=2,
            steel_mill="宝钢",
            steel_mill_id=3,
            category_name="冷轧",
            policy_type="THICKNESS",
            grade_value="DC04",
            base_thickness=Decimal("1.0"),
            price_adjustment=90,
            thick_min=Decimal("0.8"),
            thick_max=Decimal("1.2"),
            is_base=0,
            sheet_name="宝钢",
        ),
        PolicyLadderRow(
            policy_id=3,
            year=2025,
            month=3,
            steel_mill="宝钢",
            steel_mill_id=3,
            category_name="冷轧",
            policy_type="THICKNESS",
            grade_value="DC04",
            base_thickness=Decimal("1.0"),
            price_adjustment=400,
            thick_min=Decimal("0.8"),
            thick_max=Decimal("1.2"),
            is_base=0,
            sheet_name="宝钢",
        ),
    ]
    result = build_policy_mom_anomalies(rows, top_n=5)
    assert result["kind"] == "policy_anomalies"
    assert [item["month"] for item in result["items"]] == ["2025-02", "2025-03"]
    assert [item["change"] for item in result["items"]] == [40, 310]
    assert result["items"][0]["steel_mill"] == "宝钢"
    assert result["items"][0]["prev_sheet_name"] == "宝钢"
    assert result["items"][0]["sheet_name"] == "宝钢"
    assert "传错月或错档" in str(result["items"][0]["hint"])


def test_policy_jump_hint_names_changed_sheet() -> None:
    from decimal import Decimal

    from app.repositories.llm.policy_analysis_repository import PolicyLadderRow
    from app.services.llm.analysis.steel.policy import build_policy_mom_anomalies

    def row(policy_id: int, month: int, adjustment: int, sheet_name: str) -> PolicyLadderRow:
        return PolicyLadderRow(
            policy_id=policy_id,
            year=2025,
            month=month,
            steel_mill="鞍本",
            steel_mill_id=12,
            category_name="镀锌钢",
            policy_type="THICKNESS",
            grade_value="镀锌钢",
            base_thickness=Decimal("1.0"),
            price_adjustment=adjustment,
            thick_min=Decimal("0.40"),
            thick_max=Decimal("0.45"),
            is_base=0,
            sheet_name=sheet_name,
        )

    result = build_policy_mom_anomalies(
        [row(1, 1, 430, "TAGAL"), row(2, 2, 650, "鞍钢集团")],
        top_n=5,
    )
    hint = str(result["items"][0]["hint"])
    assert result["items"][0]["prev_sheet_name"] == "TAGAL"
    assert result["items"][0]["sheet_name"] == "鞍钢集团"
    assert "TAGAL" in hint
    assert "鞍钢集团" in hint
    assert "不要当成传错月或错档" in hint
    assert "建议核对是否上传错月" not in hint


def test_query_parser_policy_colloquial_anomaly() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-12"},
            "filters": {},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="2025年加减价有没有异常，是不是传错了？",
    )
    assert query.subject == "steel_price_policy"
    assert query.time_range.start == "2025-01"
    assert query.time_range.end == "2025-12"
    assert "trend" in query.analyses
    assert "drivers" in query.analyses


def _parse_without_draft_time(question: str):
    parser = QueryParser()
    db = MagicMock()
    parser._extractor.extract = MagicMock(
        return_value={"time_range": {}, "filters": {}, "compare_locations": []}
    )
    return parser.parse(db, user_question=question)


def test_query_parser_base_price_month_move_since_year_keeps_order_filter() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2026-09"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="2025年以来，青岛基地，基准价，环比相差500的有那一些",
    )
    assert query.subject == "steel_base_price"
    assert query.filters.get("month_move_over") == "500"
    assert query.filters.get("location") == "青岛"
    assert query.time_range.start == "2025-01"
    assert query.time_range.end == "2026-09"


def test_query_parser_base_price_month_move_lists_named_gap() -> None:
    query = _parse_without_draft_time("基准价，环比相差500的有那一些")
    assert query.subject == "steel_base_price"
    assert query.filters.get("month_move_over") == "500"
    assert query.time_range.start == "2000-01"
    assert query.time_range.end == "2099-12"


def test_query_parser_base_price_month_move_keeps_named_year() -> None:
    query = _parse_without_draft_time("现网基准价，按现在的月度涨跌范围，有多少条超300了？")
    assert query.filters.get("month_move_over") == "300"
    assert query.time_range.start == "2000-01"

    named_year = _parse_without_draft_time("2026年基准价环比相差200的有哪些")
    assert named_year.filters.get("month_move_over") == "200"
    assert named_year.time_range.start == "2026-01"
    assert named_year.time_range.end == "2026-12"


def test_build_base_price_month_move_over_uses_landed_price() -> None:
    from app.repositories.llm.base_price_analysis_repository import BasePricePeriodRow
    from app.services.llm.analysis.steel.base_price import build_base_price_month_move_over

    mill_ids = {
        "邯钢": 1,
        "宝钢": 2,
        "首钢": 3,
        "唐钢": 4,
        "马钢": 5,
        "包钢": 6,
        "鞍钢": 7,
        "本钢": 8,
    }

    def row(
        year: int,
        month: int,
        mill: str,
        price: str,
        *,
        location: str = "青岛",
        grade: str = "HC440/780DHD+Z",
    ):
        return BasePricePeriodRow(
            year=year,
            month=month,
            location=location,
            steel_mill=mill,
            steel_mill_id=mill_ids[mill],
            category_name="镀锌",
            grade=grade,
            spec="1.00*1250.00",
            base_price=Decimal(price),
            processing_fee=Decimal("120"),
            thick=Decimal("1.00"),
            width=Decimal("1250.00"),
        )

    rows = [
        row(2026, 1, "邯钢", "4000"),
        row(2026, 2, "邯钢", "4500"),
        row(2026, 1, "宝钢", "4000", grade="DC01"),
        row(2026, 2, "宝钢", "4600", grade="DC01"),
        row(2025, 12, "首钢", "5000", grade="HC500LAD+Z"),
        row(2026, 1, "唐钢", "5700", grade="HC500LAD+Z"),
        row(2026, 1, "马钢", "3000", location="芜湖", grade="SPHC"),
        row(2026, 1, "包钢", "3100", location="芜湖", grade="SPHC"),
        row(2026, 2, "鞍钢", "4000", location="芜湖", grade="SPHC"),
        row(2026, 1, "本钢", "2000", grade="HC180B"),
        row(2026, 3, "本钢", "4000", grade="HC180B"),
    ]
    result = build_base_price_month_move_over(
        rows,
        limit=Decimal("500"),
        window_start=(2026, 1),
    )
    assert result["count"] == 2
    lines = [str(item["line"]) for item in result["items"]]
    assert lines[0].startswith("2026年01月 青岛 HC500LAD+Z")
    assert lines[1].startswith("2026年02月 青岛 DC01")
    assert any("DC01" in line and "+600.00" in line for line in lines)
    assert any(
        "HC500LAD+Z" in line and "上月钢厂首钢" in line and "+700.00" in line for line in lines
    )
    assert all("HC440" not in line for line in lines)
    assert all("SPHC" not in line for line in lines)
    assert all("HC180B" not in line for line in lines)
