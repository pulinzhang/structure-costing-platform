from decimal import Decimal
from types import SimpleNamespace

from app.services.stamping.die_fee.calc.orchestrator.missing_die_number import (
    collect_missing_die_number_hints,
    format_missing_die_number_section,
    process_needs_die_number_hint,
)


def _process(
    *,
    seq: str = "OP10",
    code: str | None = "拉伸",
    die_number: str | None = None,
    die_length: Decimal | None = Decimal("100"),
    die_width: Decimal | None = Decimal("80"),
    die_height: Decimal | None = Decimal("50"),
) -> SimpleNamespace:
    return SimpleNamespace(
        process_seq=seq,
        process_code=code,
        die_number=die_number,
        die_length=die_length,
        die_width=die_width,
        die_height=die_height,
    )


def test_hint_when_has_dimensions_and_no_die_number() -> None:
    process = _process()
    assert process_needs_die_number_hint(process) is True


def test_no_hint_when_die_number_present() -> None:
    process = _process(die_number="T13J-OP10-001")
    assert process_needs_die_number_hint(process) is False


def test_no_hint_for_shared_process_even_with_dimensions() -> None:
    process = _process(code="共用")
    assert process_needs_die_number_hint(process) is False


def test_no_hint_when_missing_dimensions() -> None:
    process = _process(die_length=None, die_width=None, die_height=None)
    assert process_needs_die_number_hint(process) is False


def test_collect_skips_shared_and_keeps_owned() -> None:
    part = SimpleNamespace(
        part_number="502007709AA",
        stamping_supplier="合肥冲压",
        processes=[
            _process(seq="OP10", code="拉伸"),
            _process(seq="OP20", code="合并"),
        ],
    )
    hints = collect_missing_die_number_hints(part)
    assert hints == ["零件 502007709AA 工序 OP10 已有模具长/宽/高，但没有模具编号"]


def test_format_section_does_not_block() -> None:
    text = format_missing_die_number_section(["零件 A 工序 OP10 已有模具长/宽/高，但没有模具编号"])
    assert "仅提示，未拦截" in text
    assert "零件 A" in text
