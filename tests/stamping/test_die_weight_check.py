from decimal import Decimal

from app.services.stamping.die.rules.weight_check import (
    DieWeightCheckRow,
    calc_die_weight_t,
    find_die_weight_mismatches,
    format_die_weight_mismatch_issues,
)

_CHECK = Decimal("1.9895")


def _row(
    *, estimated: Decimal | None, width: Decimal | None = Decimal("1200")
) -> DieWeightCheckRow:
    return DieWeightCheckRow(
        part_number="P1",
        process_seq="OP10",
        excel_row=12,
        die_length=Decimal("880"),
        die_width=width,
        die_height=Decimal("800"),
        hollow_factor=Decimal("0.3"),
        estimated_weight_t=estimated,
    )


def test_outline_weight_example() -> None:
    assert (
        calc_die_weight_t(
            die_length=Decimal("880"),
            die_width=Decimal("1200"),
            die_height=Decimal("800"),
            hollow_factor=Decimal("0.3"),
        )
        == _CHECK
    )


def test_outline_weight_missing_size() -> None:
    assert (
        calc_die_weight_t(
            die_length=Decimal("880"),
            die_width=None,
            die_height=Decimal("800"),
            hollow_factor=Decimal("0.3"),
        )
        is None
    )


def test_same_weight_passes() -> None:
    assert find_die_weight_mismatches([_row(estimated=_CHECK)]) == []


def test_nine_percent_passes() -> None:
    stored = Decimal("1.8252")
    issues = find_die_weight_mismatches([_row(estimated=stored)])
    assert issues == []
    gap = abs(stored - _CHECK) / stored
    assert gap < Decimal("0.10")


def test_eleven_percent_rejected() -> None:
    stored = Decimal("1.7923")
    issues = find_die_weight_mismatches([_row(estimated=stored)])
    assert len(issues) == 1
    assert issues[0].relative_gap is not None
    assert issues[0].relative_gap > Decimal("0.10")
    text = format_die_weight_mismatch_issues(issues)
    assert "相对差 > 10%" in text
    assert "导入已拒绝" in text
    assert "P1" in text
    assert "OP10" in text


def test_missing_size_skipped() -> None:
    assert find_die_weight_mismatches([_row(estimated=Decimal("9"), width=None)]) == []


def test_missing_estimated_weight_skipped() -> None:
    assert find_die_weight_mismatches([_row(estimated=None)]) == []


def test_zero_stored_with_positive_check_fails() -> None:
    issues = find_die_weight_mismatches([_row(estimated=Decimal("0"))])
    assert len(issues) == 1
    assert issues[0].relative_gap is None
    assert "模具重量为 0" in format_die_weight_mismatch_issues(issues)
