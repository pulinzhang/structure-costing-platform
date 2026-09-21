"""成品核价卡：总成 / 分总成 分身份钻取。"""

from __future__ import annotations

from decimal import Decimal

from app.repositories.llm.cost_analysis.rows import L0PartPeriodRow
from app.services.llm.analysis.shared.drilldown import (
    assembly_card_role,
    build_drilldown,
    pick_finance_card,
)
from app.services.llm.analysis.shared.part_lookup import (
    build_part_existence,
    resolve_part_data_profile,
)
from app.services.llm.query.time_range import (
    asks_latest_costing,
)


def _row(
    *,
    part_number: str,
    month: int = 1,
    year: int = 2026,
    grand_total: str = "10.0000",
    is_tree_root: bool = True,
    level: int = 0,
    object_kind: str | None = None,
    root_part_number: str | None = None,
    part_name: str = "测试件",
) -> L0PartPeriodRow:
    amount = Decimal(grand_total)
    return L0PartPeriodRow(
        year=year,
        month=month,
        part_number=part_number,
        part_name=part_name,
        grand_total=amount,
        total_amount=amount,
        calc_status="ok",
        missing_leaf_count=0,
        calc_message=None,
        stamping_amount=Decimal("0"),
        purchased_amount=Decimal("0"),
        bundle_amount=Decimal("0"),
        welding_amount=Decimal("0"),
        welding_other_fee=Decimal("0"),
        indirect_amount=Decimal("0"),
        bom_version="D/09",
        should_cost=amount,
        level=level,
        is_tree_root=is_tree_root,
        object_kind=object_kind,
        location="芜湖",
        vehicle_model="T13J",
        root_part_number=root_part_number,
    )


def test_assembly_card_role() -> None:
    assert assembly_card_role(is_tree_root=True, level=0, object_kind=None) == "供货总成"
    assert assembly_card_role(is_tree_root=False, level=1, object_kind="l1_subassembly") == "分总成"
    assert assembly_card_role(is_tree_root=False, level=1, object_kind="l1_stamping") == "冲压件"


def test_pick_finance_prefers_tree_root() -> None:
    root = _row(part_number="551002784AA", is_tree_root=True, grand_total="80")
    child = _row(
        part_number="551002856AA",
        is_tree_root=False,
        level=1,
        object_kind="l1_stamping",
        grand_total="4.6065",
    )
    picked = pick_finance_card([child, root])
    assert picked.is_tree_root is True


def test_build_drilldown_keeps_assembly_and_subassembly_apart() -> None:
    rows = [
        _row(
            part_number="501002856AA",
            is_tree_root=True,
            level=0,
            grand_total="88.0000",
            part_name="横梁总成",
        ),
        _row(
            part_number="501002856AA-1",
            is_tree_root=False,
            level=1,
            object_kind="l1_subassembly",
            grand_total="12.0000",
            part_name="横梁分总成",
            root_part_number="501002856AA",
        ),
    ]
    result = build_drilldown(rows, part_number="2856")
    assert result["fork"] == "assembly"
    assert result["identity_count"] == 1
    assert result["card_role"] == "供货总成"
    assert result["latest"]["grand_total"] == "88.00"
    assert result["year"] == 2026
    assert result["month"] == 1
    branch = result["branch_identities"]
    assert len(branch) == 1
    assert branch[0]["card_role"] == "分总成"
    assert branch[0]["latest"]["grand_total"] == "12.00"
    assert branch[0]["root_part_number"] == "501002856AA"


def test_l1_stamping_card_is_not_treated_as_supply_assembly() -> None:
    rows = [
        _row(
            part_number="551002856AA",
            is_tree_root=False,
            level=1,
            object_kind="l1_stamping",
            grand_total="4.6065",
            part_name="左后门上铰链加强板",
            root_part_number="551002784AA",
        )
    ]
    profile = resolve_part_data_profile(
        l0_rows=rows,
        stamping_rows=[],
        process_rows=[],
    )
    assert profile.stamping_cost_applicable is True
    assert profile.domain_note is None

    existence = build_part_existence(
        query_token="2856",
        l0_rows=rows,
        stamping_rows=[],
        process_rows=[],
    )
    assert existence["l0"]["card_role"] == "冲压件"
    assert existence["l0"]["root_part_number"] == "551002784AA"
    assert existence["stamping_cost"]["applicable"] is True

    drilldown = build_drilldown(rows, part_number="2856")
    assert drilldown["identity_count"] == 1
    assert drilldown["fork"] == "sub_assembly"
    assert drilldown["card_role"] == "冲压件"
    assert drilldown["latest"]["grand_total"] == "4.61"
    assert drilldown["year"] == 2026
    assert drilldown["month"] == 1


def test_asks_latest_costing_uses_table_month() -> None:
    assert asks_latest_costing("2856零件，最近一次核价是多少钱？")
    assert asks_latest_costing("2856最新价")
