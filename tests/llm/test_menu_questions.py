"""按侧栏菜单逐条构造标准问句，校验 subject 与列表筛选参数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.llm.menu_catalog import SUBJECT_MENU, build_list_params
from app.services.llm.query.query_parser import QueryParser
from tests.llm.menu_question_matrix import (
    MENU_QUESTION_CASES,
    complete_cases,
    pending_cases,
)


def _mock_parser(parser: QueryParser) -> None:
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V1"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )


def _parse(case) -> tuple:
    parser = QueryParser()
    db = MagicMock()
    _mock_parser(parser)
    query = parser.parse(db, user_question=case.user_question)
    params = build_list_params(query)
    return query, params


@pytest.mark.parametrize(
    "case",
    complete_cases(),
    ids=[item.menu_label for item in complete_cases()],
)
def test_complete_menu_question_routes_correctly(case) -> None:
    query, _params = _parse(case)

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


@pytest.mark.parametrize(
    "case,expected_params",
    [
        pytest.param(
            next(c for c in complete_cases() if c.hash_page == "steel-price-policy-download"),
            {"year": "2025", "month": "1", "policy_type": "THICKNESS"},
            id="加减价政策列表",
        ),
        pytest.param(
            next(c for c in complete_cases() if c.hash_page == "base-price-download"),
            {"year": "2025", "month": "1", "location": "青岛基地"},
            id="基准价格列表",
        ),
        pytest.param(
            next(c for c in complete_cases() if c.hash_page == "winning-thickness-download"),
            {"year": "2025", "month": "1", "location": "青岛基地"},
            id="中标钢厂厚度价格一览表",
        ),
        pytest.param(
            next(c for c in complete_cases() if c.hash_page == "scrap-price"),
            {"year": "2025", "month": "1"},
            id="废料月度销售价",
        ),
        pytest.param(
            next(c for c in complete_cases() if c.hash_page == "stamping-parts"),
            {"location": "青岛"},
            id="冲压零件列表",
        ),
        pytest.param(
            next(c for c in complete_cases() if c.hash_page == "steel-price-list"),
            {
                "location": "青岛",
                "year": "2025",
                "month": "1",
                "start": "2025-01",
                "end": "2025-01",
            },
            id="冲压钢材联动价一览",
        ),
        pytest.param(
            next(c for c in complete_cases() if c.hash_page == "stamping-part-cost"),
            {
                "location": "青岛",
                "year": "2025",
                "month": "1",
                "start": "2025-01",
                "end": "2025-01",
            },
            id="冲压零件价格一览",
        ),
        pytest.param(
            next(c for c in complete_cases() if c.hash_page == "assembly-cost"),
            {
                "location": "青岛",
                "year": "2025",
                "month": "1",
                "start": "2025-01",
                "end": "2025-01",
            },
            id="总成核价一览",
        ),
    ],
)
def test_complete_menu_question_list_params(case, expected_params) -> None:
    query, params = _parse(case)
    for key, value in expected_params.items():
        if key == "policy_type":
            assert query.filters.get("policy_type") == value
            continue
        assert params.get(key) == value, f"{case.menu_label}: {key}"


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
