"""零件号模糊匹配单测。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.common.part_number import (
    extract_part_number_from_text,
    part_numbers_match,
)
from app.services.llm.query.query_parser import QueryParser


def test_extract_full_part_number() -> None:
    assert extract_part_number_from_text("501006875AA 为什么这么贵？") == "501006875AA"
    assert extract_part_number_from_text("FQ199D0616T25F19N零件价格是多少？") == "FQ199D0616T25F19N"


def test_extract_four_digit_short_code() -> None:
    assert extract_part_number_from_text("冲压件，8898，存在吗？") == "8898"


def test_extract_skips_year_in_question() -> None:
    assert extract_part_number_from_text("2026年1月青岛采购成本") is None
    assert extract_part_number_from_text("2025-01青岛") is None


def test_part_numbers_match_fuzzy() -> None:
    assert part_numbers_match("501008898AA", "8898")
    assert part_numbers_match("501008898AA", "501008898AA")
    assert not part_numbers_match("501008898AA", "1234")


def test_query_parser_short_part_number() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V3"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=["501008898AA"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-08", "end": "2026-08"},
            "filters": {},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="冲压件，8898，存在吗？",
    )
    assert query.part_number() == "501008898AA"
    assert "drilldown" in query.analyses
    assert query.subject == "part"


def test_full_part_number_existence_uses_part_subject() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V3"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=["501008898AA"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-08", "end": "2026-08"},
            "filters": {},
            "compare_locations": [],
        }
    )

    query = parser.parse(db, user_question="501008898AA，存在吗？")
    assert query.part_number() == "501008898AA"
    assert query.subject == "part"
    assert "drilldown" in query.analyses
