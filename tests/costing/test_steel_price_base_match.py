"""钢材联动：基价只按大类匹配，不按牌号。"""

from types import SimpleNamespace

from app.services.costing.steel_price.calc.category import resolve_canonical_category
from app.services.costing.steel_price.calc.steps.enrich_base_price import (
    select_base_records_for_category,
)


def _row(
    *, mill: str, price: int, row_id: int, thick: int = 1, width: int = 1250
) -> SimpleNamespace:
    return SimpleNamespace(
        id=row_id,
        grade="ignored",
        steel_mill=mill,
        thick=thick,
        width=width,
        base_price=price,
    )


def test_select_one_row_per_mill_spec_ignores_base_grade() -> None:
    candidates = [
        _row(mill="马钢", price=3742, row_id=1),
        _row(mill="马钢", price=3828, row_id=2),
        _row(mill="马钢", price=3919, row_id=3),
        _row(mill="邯钢", price=3721, row_id=10),
        _row(mill="唐钢", price=5404, row_id=20),
    ]
    picked = select_base_records_for_category(candidates)
    by_mill = {row.steel_mill: row.base_price for row in picked}
    assert by_mill == {"马钢": 3742, "邯钢": 3721, "唐钢": 5404}


def test_select_keeps_distinct_specs_of_same_mill() -> None:
    candidates = [
        _row(mill="马钢", price=3742, row_id=1, width=1250),
        _row(mill="马钢", price=3800, row_id=2, width=1500),
    ]
    picked = select_base_records_for_category(candidates)
    widths = sorted(int(row.width) for row in picked)
    assert widths == [1250, 1500]


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
