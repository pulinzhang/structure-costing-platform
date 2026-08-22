# -*- coding: utf-8 -*-
"""part_lookup 菜单键解析单测。"""

from __future__ import annotations

from app.services.llm.analysis.part_lookup import resolve_part_lookup_menu_keys


def test_l0_only_returns_single_menu_key() -> None:
    keys = resolve_part_lookup_menu_keys(
        cross_check=False,
        l0_row_count=1,
        stamping_cost_row_count=0,
        stamping_process_row_count=0,
    )
    assert keys == ("l0",)


def test_cross_check_keeps_all_menu_keys() -> None:
    keys = resolve_part_lookup_menu_keys(
        cross_check=True,
        l0_row_count=1,
        stamping_cost_row_count=0,
        stamping_process_row_count=0,
    )
    assert keys == ("l0", "stamping_part", "stamping_process")
