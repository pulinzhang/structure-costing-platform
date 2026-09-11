"""钢材联动取基价：与中标厚度一览相同，只认基价表牌号（O/0 视为同一字符）。"""

from types import SimpleNamespace

from app.common.steel_grade import grade_match_key, stored_grade
from app.services.costing.steel_price.calc.category import resolve_canonical_category
from app.services.costing.steel_price.calc.steps.enrich_base_price import (
    select_winning_base_records,
)


def _row(
    *,
    mill: str,
    price: int,
    row_id: int,
    grade: str = "ignored",
    thick: int = 1,
    width: int = 1250,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=row_id,
        grade=grade,
        steel_mill=mill,
        thick=thick,
        width=width,
        base_price=price,
    )


def test_grade_match_key_treats_letter_o_as_zero() -> None:
    assert stored_grade("  dco3  ") == "DCO3"
    assert stored_grade("QStE420TM") == "QSTE420TM"
    assert grade_match_key("DCO3") == grade_match_key("DC03")
    assert grade_match_key("DCO4") == grade_match_key("DC04")
    assert grade_match_key(" dc03 ") == "DC03"
    assert grade_match_key("DC03") != grade_match_key("DC01")


def test_select_matches_letter_o_as_digit_zero() -> None:
    candidates = [
        _row(mill="邯钢", price=3721, row_id=1, grade="DCO3"),
        _row(mill="马钢", price=3828, row_id=2, grade="DCO4"),
        _row(mill="马钢", price=3742, row_id=3, grade="DC01"),
    ]
    picked = select_winning_base_records(candidates, "DC03")
    assert [(row.steel_mill, row.grade, row.base_price) for row in picked] == [
        ("邯钢", "DCO3", 3721),
    ]
    picked_dc04 = select_winning_base_records(candidates, "DC04")
    assert [(row.steel_mill, row.grade, row.base_price) for row in picked_dc04] == [
        ("马钢", "DCO4", 3828),
    ]


def test_select_skips_grade_not_in_base_table() -> None:
    candidates = [
        _row(mill="马钢", price=3742, row_id=1, grade="DC01"),
        _row(mill="马钢", price=3828, row_id=2, grade="DC04"),
        _row(mill="马钢", price=3919, row_id=3, grade="HC180Y"),
        _row(mill="邯钢", price=3721, row_id=10, grade="DC01"),
        _row(mill="唐钢", price=5404, row_id=20, grade="HC340/590DP"),
    ]
    picked = select_winning_base_records(candidates, "DC03")
    assert picked == []


def test_select_skips_hc340_591dp_when_base_has_590() -> None:
    candidates = [
        _row(mill="唐钢", price=4126, row_id=972, grade="HC340/590DP"),
        _row(mill="唐钢", price=4591, row_id=973, grade="HC420/780DP"),
    ]
    picked = select_winning_base_records(candidates, "HC340/591DP")
    assert picked == []


def test_select_uses_exact_grade_price_only() -> None:
    candidates = [
        _row(mill="山钢", price=4130, row_id=948, grade="DC51D+Z"),
        _row(mill="山钢", price=4438, row_id=949, grade="DC53D+Z"),
        _row(mill="山钢", price=4509, row_id=952, grade="HC180YD+Z"),
        _row(mill="唐钢", price=5640, row_id=956, grade="HC420/780DPD+Z"),
    ]
    picked = select_winning_base_records(candidates, "HC180YD+Z")
    assert [(row.steel_mill, row.grade, row.base_price) for row in picked] == [
        ("山钢", "HC180YD+Z", 4509),
    ]


def test_select_keeps_one_spec_per_mill_grade() -> None:
    candidates = [
        _row(mill="马钢", price=3742, row_id=1, grade="DC01", width=1250),
        _row(mill="马钢", price=3800, row_id=2, grade="DC01", width=1500),
    ]
    picked = select_winning_base_records(candidates, "DC01")
    assert len(picked) == 1
    assert picked[0].width == 1250
    assert picked[0].base_price == 3742


def test_resolve_canonical_category_from_archive_or_literal() -> None:
    assert resolve_canonical_category("冷轧", {}) == "冷轧"
    assert resolve_canonical_category("镀锌钢", {}) == "镀锌"
    assert (
        resolve_canonical_category(
            "DC01",
            {"DC01": SimpleNamespace(category_name="冷轧")},
        )
        == "冷轧"
    )
    assert resolve_canonical_category("UNKNOWN", {}) == ""
