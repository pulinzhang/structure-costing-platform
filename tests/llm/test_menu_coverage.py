"""侧栏菜单覆盖查检。"""

from __future__ import annotations

from app.services.llm.menu_catalog import MENU_COVERAGE, SUBJECT_MENU


def test_subject_menu_has_entry_for_each_complete_coverage() -> None:
    complete = [item for item in MENU_COVERAGE if item.status == "complete"]
    assert complete, "应至少有一条 complete 覆盖项"
    for item in complete:
        assert item.subject is not None
        assert item.subject in SUBJECT_MENU
        menu = SUBJECT_MENU[item.subject]
        if item.subject == "bom_material" and item.hash_page in (
            "bom-structure",
            "bom-viz",
        ):
            assert menu.hash_page == "bom-material"
        else:
            assert menu.hash_page == item.hash_page


def test_pending_menu_items_documented() -> None:
    pending = [item for item in MENU_COVERAGE if item.status == "pending"]
    pending_pages = {item.hash_page for item in pending}
    assert "costing" in pending_pages
    assert "winning-thickness-download" not in pending_pages
    assert "scrap-price" not in pending_pages
