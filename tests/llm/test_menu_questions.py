"""按侧栏菜单逐条构造标准问句，校验 subject 与列表筛选参数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.llm.menu_catalog import SUBJECT_MENU
from app.services.llm.query.parser.pipeline import QueryParser
from tests.llm.menu_question_matrix import (
    MENU_QUESTION_CASES,
    complete_cases,
    pending_cases,
)


def _mock_parser(parser: QueryParser) -> None:
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V1"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )


def _parse(case):
    parser = QueryParser()
    db = MagicMock()
    _mock_parser(parser)
    return parser.parse(db, user_question=case.user_question)


@pytest.mark.parametrize(
    "case",
    complete_cases(),
    ids=[item.menu_label for item in complete_cases()],
)
def test_complete_menu_question_routes_correctly(case) -> None:
    query = _parse(case)

    assert query.time_range.start == "2025-01"
    assert query.time_range.end == "2025-01"
    assert query.location() == "青岛"
    assert query.subject == case.expected_subject
    assert "summary" in query.analyses

    menu = SUBJECT_MENU[case.expected_subject]
    if case.expected_subject == "bom_material" and case.hash_page in (
        "bom-structure",
        "bom-viz",
    ):
        assert menu.hash_page == "bom-material"
    else:
        assert menu.hash_page == case.hash_page


def test_menu_question_matrix_covers_all_coverage_items() -> None:
    from app.services.llm.menu_catalog import MENU_COVERAGE

    matrix_pages = {case.hash_page for case in MENU_QUESTION_CASES}
    for item in MENU_COVERAGE:
        assert item.hash_page in matrix_pages, f"缺少问句模板: {item.menu_label}"


@pytest.mark.parametrize(
    "case",
    pending_cases(),
    ids=[item.menu_label for item in pending_cases()],
)
def test_pending_menu_question_templates(case) -> None:
    """待接 subject 的菜单：问句模板已备好，解析结果暂不断言 subject。"""
    assert case.user_question.startswith("青岛基地，2025年01月，")
    assert case.user_question.endswith("的情况。")
    assert case.expected_subject is None
