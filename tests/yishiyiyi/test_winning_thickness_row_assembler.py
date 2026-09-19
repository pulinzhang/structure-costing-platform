"""中标厚度行组装：基价表驱动 × 档案大类 × 政策阶梯展开。"""

from decimal import Decimal
from types import SimpleNamespace

from app.services.yishiyiyi.winning_thickness.assemble.row_assembler import (
    WinningThicknessRowAssembler,
    _BaseContext,
    dedupe_bases_by_mill_grade,
)


def _ladder_item(*, item_id: int, sort_order: int, thick_min: str, thick_max: str, adj: int):
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


def _category_policy(*, policy_id: int = 1):
    return SimpleNamespace(
        id=policy_id,
        policy_type="THICKNESS",
        grade_type="CATEGORY",
        grade_value="冷轧钢",
        category_name="冷轧钢",
        steel_mill="唐钢",
        base_thickness=Decimal("1.00"),
        excel_filename="policy.xlsx",
        items=[
            _ladder_item(item_id=101, sort_order=1, thick_min="0.60", thick_max="0.80", adj=160),
            _ladder_item(item_id=102, sort_order=2, thick_min="0.80", thick_max="1.00", adj=120),
            _ladder_item(item_id=103, sort_order=3, thick_min="1.00", thick_max="1.20", adj=80),
        ],
    )


def test_rows_from_ladder_expands_all_intervals_per_grade():
    assembler = WinningThicknessRowAssembler()
    context = _BaseContext(
        grade="DC01",
        steel_mill="唐钢",
        location="芜湖",
        year=2026,
        month=1,
        base_price=Decimal("3700"),
        processing_fee=Decimal("120"),
        thick=Decimal("1.00"),
        spec="1.00*1250",
        base_price_id=11,
    )
    policy = _category_policy()

    rows = assembler._rows_from_ladder(
        context,
        category_name="冷轧",
        policy=policy,
        items=list(policy.items),
    )

    assert len(rows) == 3
    assert {row.grade for row in rows} == {"DC01"}
    assert [row.thickness_adjustment for row in rows] == [
        Decimal("160"),
        Decimal("120"),
        Decimal("80"),
    ]
    assert all(row.thickness_range != "-" for row in rows)


def test_two_grades_same_category_each_get_full_ladder():
    assembler = WinningThicknessRowAssembler()
    policy = _category_policy()
    policies = [policy]
    cache: dict = {}

    ctx_dc01 = _BaseContext(
        grade="DC01",
        steel_mill="唐钢",
        location="芜湖",
        year=2026,
        month=1,
        base_price=Decimal("3700"),
        processing_fee=Decimal("120"),
        thick=Decimal("1.00"),
        spec=None,
        base_price_id=1,
    )
    ctx_dc04 = _BaseContext(
        grade="DC04",
        steel_mill="唐钢",
        location="芜湖",
        year=2026,
        month=1,
        base_price=Decimal("3800"),
        processing_fee=Decimal("120"),
        thick=Decimal("1.00"),
        spec=None,
        base_price_id=2,
    )

    rows_dc01 = assembler._expand_grade_ladder(
        ctx_dc01,
        policies,
        category_name="冷轧",
        ladder_cache=cache,
    )
    rows_dc04 = assembler._expand_grade_ladder(
        ctx_dc04,
        policies,
        category_name="冷轧",
        ladder_cache=cache,
    )

    assert len(rows_dc01) == 3
    assert len(rows_dc04) == 3
    assert len(cache) == 1
    assert rows_dc01[0].grade == "DC01"
    assert rows_dc04[0].grade == "DC04"
    assert rows_dc01[0].thickness_range == rows_dc04[0].thickness_range


def test_resolve_ladder_uses_category_not_grade():
    assembler = WinningThicknessRowAssembler()
    policy = _category_policy()
    cache: dict = {}
    context = _BaseContext(
        grade="DC01",
        steel_mill="唐钢",
        location="芜湖",
        year=2026,
        month=1,
        base_price=Decimal("3800"),
        processing_fee=Decimal("120"),
        thick=Decimal("1.00"),
        spec=None,
        base_price_id=1,
    )

    resolved_policy, items = assembler._resolve_thickness_ladder(
        context,
        [policy],
        category_name="冷轧",
        ladder_cache=cache,
    )

    assert resolved_policy is policy
    assert len(items) == 3


def test_rows_from_ladder_skips_when_no_policy():
    assembler = WinningThicknessRowAssembler()
    context = _BaseContext(
        grade="DC01",
        steel_mill="唐钢",
        location="芜湖",
        year=2026,
        month=1,
        base_price=Decimal("3700"),
        processing_fee=Decimal("120"),
        thick=Decimal("1.00"),
        spec=None,
        base_price_id=11,
    )

    rows = assembler._rows_from_ladder(
        context,
        category_name="冷轧",
        policy=None,
        items=[],
    )

    assert rows == []


def test_dedupe_bases_by_mill_grade_keeps_first_spec():
    first = SimpleNamespace(grade="HC180YD+Z", steel_mill="山钢", id=1)
    second = SimpleNamespace(grade="HC180YD+Z", steel_mill="山钢", id=2)
    other = SimpleNamespace(grade="DC51D+Z", steel_mill="山钢", id=3)
    picked = dedupe_bases_by_mill_grade([first, second, other])
    assert [row.id for row in picked] == [1, 3]
