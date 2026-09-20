"""实体表列表页 ↔ subject ↔ runner 覆盖审计。"""

from __future__ import annotations

import pytest

from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.menu_catalog import ENTITY_LIST_PAGES, MENU_COVERAGE, SUBJECT_MENU


def _runner_dispatch_subjects() -> set[str]:
    runner = AnalysisRunner()
    subjects = set(runner._handlers)
    subjects.add("part")
    return subjects


@pytest.mark.parametrize(
    ("hash_page", "subject"),
    ENTITY_LIST_PAGES,
    ids=[page for page, _ in ENTITY_LIST_PAGES],
)
def test_entity_list_page_subject_in_menu(hash_page: str, subject: str) -> None:
    assert subject in SUBJECT_MENU
    menu = SUBJECT_MENU[subject]
    if hash_page in ("bom-structure", "bom-viz"):
        assert menu.hash_page == "bom-material"
    else:
        assert menu.hash_page == hash_page


def test_entity_list_subjects_covered_in_menu_coverage() -> None:
    complete_subjects = {
        item.subject
        for item in MENU_COVERAGE
        if item.status == "complete" and item.subject is not None
    }
    entity_subjects = {subject for _, subject in ENTITY_LIST_PAGES}
    missing = entity_subjects - complete_subjects
    assert not missing, f"MENU_COVERAGE 缺少 complete: {missing}"


def test_runner_dispatches_all_entity_list_subjects() -> None:
    dispatched = _runner_dispatch_subjects()
    # l0 / cost_total 走 run() 默认分支 _run_l0
    dispatched.add("l0")
    dispatched.add("cost_total")
    entity_subjects = {subject for _, subject in ENTITY_LIST_PAGES}
    missing = entity_subjects - dispatched
    assert not missing, f"AnalysisRunner.run 未分发: {missing}"


def test_runner_has_repos_for_bom_subjects() -> None:
    runner = AnalysisRunner()
    assert hasattr(runner._bom, "_bom_material_repo")
    assert hasattr(runner._welding, "_welding_breakdown_repo")
    assert hasattr(runner._welding, "_l0_welding_fee_repo")
    assert hasattr(runner._ops, "_ops_workbench_repo")
    assert hasattr(runner._ops, "_die_fee_repo")
    assert hasattr(runner._ops, "_gauge_fee_repo")
    assert hasattr(runner._ops, "_procurement_object_repo")
    assert hasattr(runner._ops, "_engineering_change_repo")
