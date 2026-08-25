"""年份/年月不得误判为零件号。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.common.part_number import (
    extract_part_number_from_text,
    is_temporal_part_number_token,
    sanitize_part_number_token,
)
from app.services.llm.query.entity_aligner import EntityAligner
from app.services.llm.query.query_parser import QueryParser
from tests.llm.menu_question_matrix import MENU_QUESTION_CASES


@pytest.mark.parametrize(
    "token",
    [
        "2025",
        "2026",
        "2027",
        "1999",
        "2025-01",
        "2026-08",
        "202501",
        "202508",
        "20250101",
        "20251231",
    ],
)
def test_is_temporal_part_number_token_years_and_months(token: str) -> None:
    assert is_temporal_part_number_token(token)


@pytest.mark.parametrize(
    "token",
    [
        "501006875AA",
        "8898",
        "501006873AA",
        "1234",
        "50100687",
    ],
)
def test_is_temporal_part_number_token_real_parts(token: str) -> None:
    assert not is_temporal_part_number_token(token)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("青岛基地，2025年01月，成品成本的情况。", None),
        ("青岛 2025年1月 T28 成品成本动因", None),
        ("2025-01 青岛采购成本", None),
        ("2025年01月钢材联动价", None),
        ("20250101 批量上传", None),
        ("2026年1月青岛采购成本", None),
        ("501006873AA 2025年为什么涨了", "501006873AA"),
        ("冲压件，8898，存在吗？", "8898"),
    ],
)
def test_extract_part_number_skips_temporal(question: str, expected: str | None) -> None:
    assert extract_part_number_from_text(question) == expected


def test_sanitize_part_number_token() -> None:
    assert sanitize_part_number_token("2025") is None
    assert sanitize_part_number_token("2025-01") is None
    assert sanitize_part_number_token("501006875aa") == "501006875AA"


def _mock_parser(parser: QueryParser) -> None:
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["D/00"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])


@pytest.mark.parametrize(
    ("llm_part_number", "question"),
    [
        ("2025", "青岛 2025年1月成品成本"),
        ("2026", "青岛 T28 近6个月趋势"),
        ("2025-01", "青岛基地，2025年01月，成品成本的情况。"),
        ("202501", "2025年01月冲压件成本"),
        ("2027", "2027年规划"),
    ],
)
def test_query_parser_strips_temporal_part_from_llm_filters(
    llm_part_number: str,
    question: str,
) -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_parser(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛", "part_number": llm_part_number},
            "compare_locations": [],
        }
    )
    query = parser.parse(db, user_question=question)
    assert query.part_number() is None
    assert query.subject != "part"


def test_entity_aligner_skips_temporal_part_mention() -> None:
    aligner = EntityAligner()
    db = MagicMock()
    aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])
    result = aligner.align(
        db,
        mentions=[("part_number", "2025"), ("part_number", "2025-01")],
    )
    assert "part_number" not in result.filters
    assert result.unresolved_mentions == []


def test_menu_questions_do_not_resolve_temporal_part_numbers() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_parser(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )
    for case in MENU_QUESTION_CASES:
        if case.status != "complete":
            continue
        query = parser.parse(db, user_question=case.user_question)
        part_number = query.part_number()
        assert part_number is None or not is_temporal_part_number_token(part_number)
