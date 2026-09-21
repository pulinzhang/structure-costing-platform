"""遍历问句矩阵：解析 → 取数 → Snapshot（mock 条件抽取，对齐库内 Scope）。"""

from __future__ import annotations

import pytest

from app.common.part_number import is_temporal_part_number_token
from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.context.snapshot_builder import SnapshotBuilder
from app.services.llm.menu_catalog import SUBJECT_MENU
from app.services.llm.query.parser.pipeline import QueryParser
from app.services.llm.usage.runner import UsageHelpRunner
from tests.llm.traversal_question_matrix import (
    TraversalCase,
    TraversalScope,
    _pick_scope,
    build_traversal_cases,
    load_traversal_cases,
    mock_extractor_draft,
)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "traversal_case" in metafunc.fixturenames:
        cases = load_traversal_cases()
        metafunc.parametrize(
            "traversal_case",
            cases,
            ids=[item.case_id for item in cases],
        )


@pytest.fixture(scope="module")
def traversal_scope() -> TraversalScope:
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        return _pick_scope(db)
    finally:
        db.close()


def _parser_with_mock(scope: TraversalScope, case: TraversalCase) -> QueryParser:
    from unittest.mock import MagicMock

    parser = QueryParser()
    if case.category != "usage":
        draft = mock_extractor_draft(case, scope)
        parser._extractor.extract = MagicMock(return_value=draft)
    return parser


@pytest.mark.integration
def test_traversal_question_matrix_not_empty(traversal_scope: TraversalScope) -> None:
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        cases = build_traversal_cases(db)
    finally:
        db.close()
    assert len(cases) >= len(SUBJECT_MENU)
    menu_ids = {c.case_id for c in cases if c.category == "menu"}
    assert "menu_assembly-cost" in menu_ids


@pytest.mark.integration
def test_traversal_pipeline(traversal_case: TraversalCase, traversal_scope: TraversalScope) -> None:
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        parser = _parser_with_mock(traversal_scope, traversal_case)
        query = parser.parse(db, user_question=traversal_case.user_question)

        part_number = query.part_number()
        assert not (
            part_number and is_temporal_part_number_token(part_number)
        ), f"误将时间识别为零件号: {part_number}"

        if traversal_case.expected_subject is not None:
            assert query.subject == traversal_case.expected_subject

        if traversal_case.expected_hash_page and traversal_case.expected_subject:
            menu = SUBJECT_MENU.get(traversal_case.expected_subject)
            assert menu is not None
            if traversal_case.expected_subject == "bom_material":
                if traversal_case.expected_hash_page in ("bom-structure", "bom-viz"):
                    assert menu.hash_page == "bom-material"
                else:
                    assert menu.hash_page == traversal_case.expected_hash_page
            else:
                assert menu.hash_page == traversal_case.expected_hash_page

        if query.query_mode == "usage_help":
            run = UsageHelpRunner().run(query)
            snapshot = SnapshotBuilder().build(query=query, run=run)
            assert snapshot.meta.has_data is True
            return

        run = AnalysisRunner().run(db, query)
        snapshot = SnapshotBuilder().build(query=query, run=run)

        if traversal_case.expect_has_data is True:
            assert run.has_data, run.data_message or "期望有数据"
            assert snapshot.meta.has_data
            if query.query_mode != "usage_help":
                assert run.summary is not None, "有数据时 summary 不应为空"

        if traversal_case.expect_has_data is False:
            assert not run.has_data, f"期望无数据但 has_data=True: {run.data_message}"
    finally:
        db.close()
