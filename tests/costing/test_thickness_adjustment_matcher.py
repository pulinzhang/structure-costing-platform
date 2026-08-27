"""厚度加减价：牌号已解析为大类后，锁定一条 CATEGORY 政策再按料厚落档。"""

from decimal import Decimal
from types import SimpleNamespace

from app.services.costing.steel_price.calc.models import CalcRow
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
        base_thickness=Decimal(base_thickness),
        excel_filename="policy.xlsx",
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
    assert "未命中厚度加减价政策" in row.messages


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
    assert "牌号未分类" in row.messages[0]
