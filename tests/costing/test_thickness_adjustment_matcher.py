"""厚度加减价：牌号已解析为大类后，锁定一条 CATEGORY 政策再按料厚落档。"""

from decimal import Decimal
from types import SimpleNamespace

from app.services.costing.steel_price.calc.models import CalcRow
from app.services.costing.steel_price.calc.status import (
    collect_row_warnings,
    summarize_thickness_outcomes,
)
from app.services.costing.steel_price.calc.steps.adjustments.thickness import (
    ThicknessAdjustmentMatcher,
)


def _item(*, item_id: int, sort_order: int, thick_min: str, thick_max: str, adj: int):
    return SimpleNamespace(
        id=item_id,
        sort_order=sort_order,
        thick_min=Decimal(thick_min),
        thick_min_operator=">=",
        thick_max=Decimal(thick_max),
        thick_max_operator="<",
        price_adjustment=adj,
        excel_row=10 + item_id,
        excel_col=3,
    )


_MILL_IDS = {"唐钢": 1, "鞍本": 2, "鞍神": 3}


def _policy(
    *,
    policy_id: int,
    base_thickness: str,
    items: list,
    mill: str = "唐钢",
    category_name: str = "冷轧钢",
):
    return SimpleNamespace(
        id=policy_id,
        policy_type="THICKNESS",
        grade_type="CATEGORY",
        grade_value=category_name,
        category_name=category_name,
        steel_mill=mill,
        steel_mill_id=_MILL_IDS[mill],
        base_thickness=Decimal(base_thickness),
        excel_filename="policy.xlsx",
        sheet_name="唐钢厚度",
        items=items,
    )


def _row(
    *,
    thickness: str,
    base_thickness: str = "1.00",
    category_name: str = "冷轧",
    mill: str = "唐钢",
    grade: str = "DC01",
) -> CalcRow:
    return CalcRow(
        year=2026,
        month=1,
        location="芜湖",
        grade=grade,
        thickness=Decimal(thickness),
        steel_mill=mill,
        steel_mill_id=_MILL_IDS[mill],
        category_name=category_name,
        base_thickness=Decimal(base_thickness),
        width=Decimal("1250"),
        base_price=Decimal("3700"),
    )


def test_matcher_hits_ladder_on_locked_category_policy() -> None:
    preferred = _policy(
        policy_id=1,
        base_thickness="1.00",
        items=[
            _item(item_id=101, sort_order=1, thick_min="0.60", thick_max="0.80", adj=160),
            _item(item_id=102, sort_order=2, thick_min="0.80", thick_max="1.20", adj=80),
        ],
    )
    matcher = ThicknessAdjustmentMatcher()
    row = _row(thickness="0.70")

    assert matcher.apply(row, [preferred]) is True
    assert row.thickness_adjustment == Decimal("160")
    assert row.thickness_policy_id == 1
    assert row.thickness_ladder_item_id == 101
    assert row.thickness_excel_filename == "policy.xlsx"
    assert row.thickness_steel_mill == "唐钢"
    assert row.thickness_sheet_name == "唐钢厚度"
    assert row.thickness_excel_row == 111
    assert row.thickness_excel_col == 3


def test_matcher_does_not_fall_through_to_other_base_thickness_policy() -> None:
    preferred = _policy(
        policy_id=1,
        base_thickness="1.00",
        items=[
            _item(item_id=101, sort_order=1, thick_min="0.60", thick_max="0.80", adj=160),
        ],
    )
    fallback = _policy(
        policy_id=2,
        base_thickness="1.50",
        items=[
            _item(item_id=201, sort_order=1, thick_min="1.00", thick_max="2.00", adj=40),
        ],
    )
    matcher = ThicknessAdjustmentMatcher()
    row = _row(thickness="1.20", base_thickness="1.00")

    assert matcher.apply(row, [preferred, fallback]) is False
    assert row.thickness_policy_id is None
    assert row.thickness_adjustment == Decimal("0")
    assert "未落入该政策阶梯" in row.messages[0]
    assert "唐钢" in row.messages[0]
    assert "1.2" in row.messages[0]


def test_matcher_requires_archive_category() -> None:
    policy = _policy(
        policy_id=1,
        base_thickness="1.00",
        items=[
            _item(item_id=101, sort_order=1, thick_min="0.60", thick_max="0.80", adj=160),
        ],
    )
    matcher = ThicknessAdjustmentMatcher()
    row = _row(thickness="0.70", category_name="")

    assert matcher.apply(row, [policy]) is False
    assert "这个牌号还没分类" in row.messages[0]


def test_matcher_skips_mill_without_thickness_block() -> None:
    policy = _policy(
        policy_id=1,
        mill="鞍本",
        base_thickness="1.00",
        items=[
            _item(item_id=101, sort_order=1, thick_min="0.60", thick_max="0.80", adj=160),
        ],
    )
    matcher = ThicknessAdjustmentMatcher()
    row = _row(thickness="0.70", mill="鞍神")
    row.base_price_id = 1

    assert matcher.apply(row, [policy]) is False
    assert row.messages == []
    assert row.thickness_applicable is False
    assert row.thickness_policy_id is None
    row.finalize_status()
    assert row.match_status == "base_only"
    assert row.calc_status == "success"
    assert row.calc_message is None


def test_matcher_explains_category_missing_for_mill() -> None:
    policy = _policy(
        policy_id=1,
        mill="唐钢",
        category_name="镀锌钢",
        base_thickness="1.00",
        items=[
            _item(item_id=101, sort_order=1, thick_min="0.60", thick_max="0.80", adj=160),
        ],
    )
    matcher = ThicknessAdjustmentMatcher()
    row = _row(thickness="0.70", category_name="冷轧", mill="唐钢")

    assert matcher.apply(row, [policy]) is False
    message = row.messages[0]
    assert "没有大类「冷轧」" in message
    assert "镀锌钢" in message


def test_collect_row_warnings_includes_mill_and_category() -> None:
    row = _row(thickness="0.70", mill="唐钢", category_name="冷轧")
    row.add_message("钢厂「唐钢」本期厚度政策没有大类「冷轧」（该厂政策大类：镀锌钢）")
    warnings = collect_row_warnings([row], keyword="厚度")
    assert warnings == [
        "唐钢 · 冷轧 · DC01 0.7*1250 钢厂「唐钢」本期厚度政策没有大类「冷轧」（该厂政策大类：镀锌钢）"
    ]


def test_thickness_hit_is_success_without_width() -> None:
    row = _row(thickness="0.70")
    row.base_price_id = 1
    row.thickness_policy_id = 10
    row.finalize_status()
    assert row.match_status == "full_match"
    assert row.calc_status == "success"


def test_summarize_thickness_outcomes_separates_skip_from_miss() -> None:
    hit = _row(thickness="0.70", mill="唐钢")
    hit.thickness_policy_id = 1
    skip = _row(thickness="0.70", mill="鞍神")
    skip.thickness_applicable = False
    miss = _row(thickness="0.70", mill="唐钢", grade="DC04")
    miss.add_message("钢厂「唐钢」本期厚度政策没有大类「冷轧」")
    summary = summarize_thickness_outcomes([hit, skip, miss])
    assert summary == {
        "hit": 1,
        "skip": 1,
        "miss": 1,
        "skip_mills": ["鞍神"],
    }
