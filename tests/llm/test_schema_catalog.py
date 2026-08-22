# -*- coding: utf-8 -*-
"""SchemaCatalog 单元测试（不调 LLM、不改库）。"""

from __future__ import annotations

import pytest

from app.schemas.vo.l0_assembly_cost_vo import L0AssemblyCostVO
from app.services.llm.catalog import (
    build_merged_pack_schema_card,
    build_pack_schema_card,
    build_schema_card,
    format_schema_card_markdown,
    project_mapping,
    schema_card_fingerprint,
)


def test_extract_l0_allowlist_keeps_vo_keys_only() -> None:
    card = build_schema_card(
        [L0AssemblyCostVO],
        allowlist=frozenset({"grand_total", "total_amount", "calc_status"}),
    )
    names = card.field_names()
    assert names == frozenset({"grand_total", "total_amount", "calc_status"})
    by_name = {field.name: field for field in card.fields}
    assert by_name["grand_total"].is_money is True
    assert "元" in by_name["grand_total"].label_zh
    assert "万元" not in by_name["grand_total"].label_zh


def test_dashboard_pack_card_includes_aggregates() -> None:
    card = build_pack_schema_card("dashboard")
    names = card.field_names()
    assert "grand_total" in names
    assert "grand_total_sum" in names
    assert "L0AssemblyCostVO" in card.model_names
    markdown = format_schema_card_markdown(card)
    assert "字段词典" in markdown
    assert "禁止改为万元" in markdown
    assert "`grand_total`" in markdown


def test_project_mapping_strips_unknown_keys() -> None:
    card = build_pack_schema_card("steel")
    allowed = card.field_names()
    cleaned = project_mapping(
        {
            "final_price_per_ton": "5100.0000",
            "invented_wan_yuan": "1.2",
            "location": "青岛",
        },
        allowed,
    )
    assert "invented_wan_yuan" not in cleaned
    assert cleaned["location"] == "青岛"


def test_unknown_pack_raises() -> None:
    with pytest.raises(KeyError):
        build_pack_schema_card("not_a_real_pack")


def test_all_report_pack_ids_have_schema_cards() -> None:
    from app.services.llm.context.pack_catalog import REPORT_PACK_MAP

    for report_type, pack_ids in REPORT_PACK_MAP.items():
        card = build_merged_pack_schema_card(list(pack_ids))
        assert card.fields, f"{report_type} schema empty"
        assert "scope_meta" not in {f.name for f in card.fields}


def test_scope_meta_pack_card() -> None:
    card = build_pack_schema_card("scope_meta")
    names = card.field_names()
    assert "location" in names
    assert "hard_stop" in names
    assert "l0_count" in names


def test_merged_fingerprint_stable() -> None:
    card_a = build_merged_pack_schema_card(["dashboard", "steel"])
    card_b = build_merged_pack_schema_card(["dashboard", "steel"])
    assert schema_card_fingerprint(card_a) == schema_card_fingerprint(card_b)
    assert len(schema_card_fingerprint(card_a)) == 16
