from decimal import Decimal

from app.services.stamping.die_fee.export.columns import COL_COUNT, HEADERS, WIDTHS
from app.services.stamping.die_fee.export.values import _check_weight_formula
from app.services.stamping.die_fee.rules.fee_math import (
    calc_line_die_fee,
    is_progressive_mode,
    resolve_final_die_fee,
    resolve_price_kind,
)


def test_line_die_fee_example() -> None:
    line = calc_line_die_fee(
        estimated_weight_t=Decimal("2"),
        unit_price=Decimal("5"),
        alloc_ratio=Decimal("1"),
        allocation_qty=Decimal("10"),
    )
    assert line == Decimal("1.0000")


def test_skip_zero_weight() -> None:
    assert (
        calc_line_die_fee(
            estimated_weight_t=Decimal("0"),
            unit_price=Decimal("5"),
            alloc_ratio=Decimal("1"),
            allocation_qty=Decimal("10"),
        )
        is None
    )


def test_progressive_from_production_mode() -> None:
    assert is_progressive_mode("级进模")
    assert resolve_price_kind("级进模自动") == "progressive"
    assert resolve_price_kind("钢板模") == "steel_plate"
    assert resolve_price_kind("铸造模") == "steel_plate"


def test_final_fee_allows_zero_not_used_for_negative_check() -> None:
    assert resolve_final_die_fee(Decimal("1.0000"), Decimal("-1.0000")) == Decimal("0.0000")
    assert resolve_final_die_fee(Decimal("1.0000"), Decimal("-0.5000")) == Decimal("0.5000")


def test_check_weight_excel_formula() -> None:
    formula = _check_weight_formula(6)
    assert formula.startswith("=IF(COUNT(Z6,AA6,AB6,AC6)=4,")
    assert "Z6*AA6*AB6*AC6*7.85/1000000000" in formula
    assert "^" not in formula
    assert len(HEADERS) == COL_COUNT == len(WIDTHS)
    assert HEADERS[4] == "供应商"
    assert HEADERS[5] == "版本"
    assert HEADERS[6] == "零件号"
    assert HEADERS[16] == "最终模具费"
