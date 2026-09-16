"""上一问范围沿用（不调真实 LLM）。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.schemas.llm.analysis_query import SCOPE_UNSET, AnalysisQuery, TimeRange
from app.schemas.vo.user_vo import UserVO
from app.services.llm.analysis.shared.idempotency import build_idempotency_key
from app.services.llm.client import LlmClientError
from app.services.llm.comparison_basis import default_comparison_basis
from app.services.llm.query.query_parser import QueryParser
from app.services.llm.report_service import (
    LlmAnalysisReportService,
    analysis_query_from_report_fields,
)


def _previous(
    *,
    start: str = "2026-01",
    end: str = "2026-08",
    filters: dict[str, str] | None = None,
    subject: str = "cost_total",
    query_mode: str = "analysis",
) -> AnalysisQuery:
    return AnalysisQuery(
        time_range=TimeRange(start=start, end=end),
        filters=filters
        or {
            "location": "青岛",
            "vehicle_model": "T28",
            "bom_version": "V1",
        },
        subject=subject,
        comparison_basis=default_comparison_basis(same_bom_version=True),
        analyses=["summary", "trend"],
        user_question="去年问句",
        query_mode=query_mode,  # type: ignore[arg-type]
    )


def _mock_aligner(parser: QueryParser) -> None:
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛", "济南"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛", "济南": "济南"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28", "T27"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V1", "V2"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])


def _parser_with_draft(draft: dict[str, object]) -> tuple[QueryParser, MagicMock]:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(return_value=draft)
    return parser, db


def test_carry_that_qingdao_keeps_vehicle_and_range() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {"location": "青岛", "vehicle_model": "T27"},
            "compare_locations": [],
        }
    )
    query = parser.parse(db, user_question="那青岛呢", previous_query=_previous())
    assert query.location() == "青岛"
    assert query.vehicle_model() == "T28"
    assert query.time_range.start == "2026-01"
    assert query.time_range.end == "2026-08"
    assert query.parser_data_message and "沿用上一问时间" in query.parser_data_message


def test_carry_where_expensive_keeps_scope_and_adds_drivers() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {},
            "compare_locations": [],
        }
    )
    query = parser.parse(db, user_question="贵在哪", previous_query=_previous())
    assert query.location() == "青岛"
    assert query.vehicle_model() == "T28"
    assert query.time_range.start == "2026-01"
    assert "drivers" in query.analyses


def test_carry_aggregate_drops_part_number() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {"location": "青岛", "vehicle_model": "T28"},
            "compare_locations": [],
        }
    )
    previous = _previous(
        filters={
            "location": "青岛",
            "vehicle_model": "T28",
            "part_number": "501006875AA",
        }
    )
    query = parser.parse(db, user_question="青岛 T28 总体怎么样", previous_query=previous)
    assert query.part_number() is None
    assert query.location() == "青岛"


def test_carry_location_change_drops_compare_locations() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {"location": "济南"},
            "compare_locations": [],
        }
    )
    previous = _previous(
        filters={
            "location": "青岛",
            "vehicle_model": "T28",
            "compare_locations": "青岛,济南",
        }
    )
    query = parser.parse(db, user_question="那济南呢", previous_query=previous)
    assert query.location() == "济南"
    assert query.vehicle_model() == "T28"
    assert query.filter_get("compare_locations") is None


def test_carry_vehicle_change_drops_bom_version() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {"vehicle_model": "T27"},
            "compare_locations": [],
        }
    )
    query = parser.parse(db, user_question="那 T27 呢", previous_query=_previous())
    assert query.vehicle_model() == "T27"
    assert query.bom_version() is None
    assert query.location() == "青岛"


def test_carry_usage_help_ignores_previous() -> None:
    parser, db = _parser_with_draft({"time_range": {}, "filters": {}, "compare_locations": []})
    query = parser.parse(db, user_question="怎么上传工艺", previous_query=_previous())
    assert query.query_mode == "usage_help"
    assert query.filters == {}


def test_carry_explicit_time_drops_part_number() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-03", "end": "2026-03"},
            "filters": {},
            "compare_locations": [],
        }
    )
    previous = _previous(
        filters={
            "location": "青岛",
            "vehicle_model": "T28",
            "bom_version": "V1",
            "part_number": "501006875AA",
        }
    )
    query = parser.parse(db, user_question="2026年3月的情况", previous_query=previous)
    assert query.time_range.start == "2026-03"
    assert query.part_number() is None
    assert query.bom_version() is None
    assert query.location() == "青岛"


def test_carry_skips_scope_unset_placeholder() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {},
            "compare_locations": [],
        }
    )
    previous = _previous(
        filters={
            "location": SCOPE_UNSET,
            "vehicle_model": "T28",
        }
    )
    query = parser.parse(db, user_question="贵在哪", previous_query=previous)
    assert query.location() is None
    assert query.vehicle_model() == "T28"


def test_carry_pin_latest_skips_previous_range() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {},
            "compare_locations": [],
        }
    )
    parser._cost_repo.query_latest_card_scope = MagicMock(
        return_value=SimpleNamespace(
            year=2026,
            month=3,
            location="青岛",
            vehicle_model="T28",
            bom_version="V1",
        )
    )
    previous = _previous(
        filters={
            "location": "青岛",
            "vehicle_model": "T28",
            "part_number": "501006875AA",
        }
    )
    query = parser.parse(db, user_question="这个多少钱", previous_query=previous)
    assert query.part_number() == "501006875AA"
    assert query.time_range.start == "2026-03"
    assert query.time_range.end == "2026-03"


def test_carry_extract_failure_keeps_previous_filters() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(side_effect=LlmClientError("down"))
    query = parser.parse(db, user_question="贵在哪", previous_query=_previous())
    assert query.location() == "青岛"
    assert query.filters != {}
    assert query.parser_fallback_level == 4


def test_carry_ellipsis_keeps_subject() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {"location": "青岛"},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="那青岛呢",
        previous_query=_previous(subject="stamping_part"),
    )
    assert query.subject == "stamping_part"


def test_carry_ne_particle_does_not_keep_stamping_subject() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {"location": "青岛", "vehicle_model": "T28"},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="青岛 T28 采购成本怎么样呢",
        previous_query=_previous(
            subject="stamping_part",
            filters={
                "location": "青岛",
                "vehicle_model": "T28",
                "part_number": "501006875AA",
            },
        ),
    )
    assert query.subject != "stamping_part"
    assert query.part_number() is None


def test_carry_without_previous_uses_draft_time() -> None:
    parser, db = _parser_with_draft(
        {
            "time_range": {"start": "2026-09", "end": "2026-09"},
            "filters": {"location": "青岛"},
            "compare_locations": [],
        }
    )
    query = parser.parse(db, user_question="成本怎么样")
    assert query.location() == "青岛"
    assert query.time_range.start == "2026-09"


def test_reconstruct_query_from_flat_scope() -> None:
    query = analysis_query_from_report_fields(
        query_json=None,
        location="青岛",
        year=2026,
        month=8,
        vehicle_model="T28",
        bom_version="V1",
        part_number="501006875AA",
        resolved_report_type="summary,trend",
    )
    assert query is not None
    assert query.time_range.start == "2026-08"
    assert query.part_number() == "501006875AA"


def test_load_previous_query_ignores_missing_and_other_user() -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    current = UserVO(
        id=1,
        username="u1",
        is_active=True,
        is_admin=False,
        permissions=[],
    )
    service.repository.get_by_id = MagicMock(return_value=None)
    assert service._load_previous_query(db, previous_report_id=9, current_user=current) is None
    other = SimpleNamespace(user_id=2, query_json=None)
    service.repository.get_by_id = MagicMock(return_value=other)
    assert service._load_previous_query(db, previous_report_id=9, current_user=current) is None


def test_idempotency_key_includes_start_and_filter_hash() -> None:
    key = build_idempotency_key(
        report_type="auto",
        audience="buyer",
        user_question="那济南呢",
        user_id=1,
        time_range_start="2026-01",
        time_range_end="2026-08",
        filters={"location": "济南", "vehicle_model": "T28"},
    )
    assert "|2026-01|" in key
    assert "|f:" in key
    assert len(key) <= 200
    other = build_idempotency_key(
        report_type="auto",
        audience="buyer",
        user_question="那济南呢",
        user_id=1,
        time_range_start="2026-08",
        time_range_end="2026-08",
        filters={"location": "济南", "vehicle_model": "T28"},
    )
    assert key != other
