from decimal import Decimal
from types import SimpleNamespace

from app.services.stamping.die_fee.calc.part_calculator import DieFeePartCalculator
from app.services.stamping.die_fee.calc.weight_resolver import (
    PreviousWeightIndex,
    can_inherit_previous_weight,
    index_resolved_weights,
    resolve_part_weights,
)
from app.services.stamping.die_fee.fee_math import build_line_basis_text


def _process(
    *,
    seq: str,
    code: str | None = None,
    weight: Decimal | None = None,
    order: int = 1,
    ratio: Decimal = Decimal("0.50"),
    process_id: int = 1,
    die_length: Decimal | None = None,
    die_width: Decimal | None = None,
    die_height: Decimal | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=process_id,
        process_seq=seq,
        process_order=order,
        process_code=code,
        estimated_weight_t=weight,
        alloc_ratio=ratio,
        die_sets=1,
        die_length=die_length,
        die_width=die_width,
        die_height=die_height,
    )


def _with_dims(
    *,
    seq: str,
    code: str | None = None,
    weight: Decimal | None = None,
    order: int = 1,
    ratio: Decimal = Decimal("0.50"),
    process_id: int = 1,
) -> SimpleNamespace:
    return _process(
        seq=seq,
        code=code,
        weight=weight,
        order=order,
        ratio=ratio,
        process_id=process_id,
        die_length=Decimal("100"),
        die_width=Decimal("80"),
        die_height=Decimal("50"),
    )


def _part(
    *,
    number: str,
    processes: list[SimpleNamespace],
    die_method: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        part_number=number,
        die_method=die_method,
        production_mode="手工线",
        processes=processes,
    )


def test_shared_row_inherits_previous_same_seq_weight() -> None:
    right = _part(
        number="RIGHT",
        processes=[_process(seq="OP10", code="共用", weight=None, ratio=Decimal("0.50"))],
    )
    assert can_inherit_previous_weight(right, right.processes[0])
    previous = PreviousWeightIndex(by_seq={"OP10": Decimal("2")}, part_number="LEFT")
    resolved = resolve_part_weights(right, previous)
    assert resolved["OP10"].weight_t == Decimal("2")
    assert resolved["OP10"].source == "inherited"
    assert resolved["OP10"].inherited_from_part_number == "LEFT"


def test_own_weight_not_replaced() -> None:
    part = _part(
        number="P",
        processes=[_process(seq="OP10", code="共用", weight=Decimal("1.2"))],
    )
    previous = PreviousWeightIndex(by_seq={"OP10": Decimal("9")}, part_number="LEFT")
    resolved = resolve_part_weights(part, previous)
    assert resolved["OP10"].weight_t == Decimal("1.2")
    assert resolved["OP10"].source == "self"


def test_no_marker_does_not_inherit() -> None:
    part = _part(
        number="P",
        processes=[_process(seq="OP10", code="DR", weight=None)],
        die_method="单干",
    )
    previous = PreviousWeightIndex(by_seq={"OP10": Decimal("2")}, part_number="LEFT")
    assert resolve_part_weights(part, previous) == {}


def test_shared_part_enters_fee_result() -> None:
    calculator = DieFeePartCalculator()
    left = _part(
        number="LEFT",
        processes=[
            _with_dims(
                seq="OP10", code="BL", weight=Decimal("2"), ratio=Decimal("0.50"), process_id=11
            )
        ],
    )
    right = _part(
        number="RIGHT",
        processes=[
            _process(seq="OP10", code="共用", weight=None, ratio=Decimal("0.50"), process_id=22)
        ],
        die_method="左右合并",
    )
    left_result, previous = calculator.calc_part(
        left,
        steel_plate_unit_price=Decimal("5"),
        progressive_die_unit_price=Decimal("6"),
        allocation_qty=Decimal("10"),
    )
    assert left_result is not None
    assert left_result[0] == Decimal("0.5000")
    right_result, _next = calculator.calc_part(
        right,
        steel_plate_unit_price=Decimal("5"),
        progressive_die_unit_price=Decimal("6"),
        allocation_qty=Decimal("10"),
        previous_weights=previous,
    )
    assert right_result is not None
    die_fee, _kind, _price, lines = right_result
    assert die_fee == Decimal("0.5000")
    assert lines[0].estimated_weight_t == Decimal("2")
    assert "继承 LEFT OP10" in lines[0].basis_text


def test_chain_without_previous_dimensions_does_not_inherit() -> None:
    calculator = DieFeePartCalculator()
    first = _part(
        number="A",
        processes=[_with_dims(seq="OP10", code="BL", weight=Decimal("2"), ratio=Decimal("0.50"))],
    )
    second = _part(
        number="B",
        processes=[_process(seq="OP10", code="共用", weight=None, ratio=Decimal("0.50"))],
        die_method="双槽",
    )
    third = _part(
        number="C",
        processes=[_process(seq="OP10", code="共用", weight=None, ratio=Decimal("0.50"))],
        die_method="双槽",
    )
    _r1, prev = calculator.calc_part(
        first,
        steel_plate_unit_price=Decimal("5"),
        progressive_die_unit_price=Decimal("6"),
        allocation_qty=Decimal("10"),
    )
    _r2, prev = calculator.calc_part(
        second,
        steel_plate_unit_price=Decimal("5"),
        progressive_die_unit_price=Decimal("6"),
        allocation_qty=Decimal("10"),
        previous_weights=prev,
    )
    assert _r2 is not None
    r3, _ = calculator.calc_part(
        third,
        steel_plate_unit_price=Decimal("5"),
        progressive_die_unit_price=Decimal("6"),
        allocation_qty=Decimal("10"),
        previous_weights=prev,
    )
    assert r3 is None


def test_previous_weight_without_dimensions_not_indexed() -> None:
    left = _part(
        number="LEFT",
        processes=[_process(seq="OP10", code="BL", weight=Decimal("2"))],
    )
    resolved = resolve_part_weights(left, PreviousWeightIndex())
    index = index_resolved_weights(left, resolved)
    assert index.by_seq == {}


def test_previous_with_dimensions_is_indexed() -> None:
    left = _part(
        number="LEFT",
        processes=[_with_dims(seq="OP10", code="BL", weight=Decimal("2"))],
    )
    resolved = resolve_part_weights(left, PreviousWeightIndex())
    index = index_resolved_weights(left, resolved)
    assert index.by_seq["OP10"] == Decimal("2")


def test_basis_text_mentions_inherit() -> None:
    text = build_line_basis_text(
        estimated_weight_t=Decimal("2"),
        unit_price=Decimal("5"),
        alloc_ratio=Decimal("0.50"),
        allocation_qty=Decimal("10"),
        line_die_fee=Decimal("0.5"),
        inherited_from_part_number="LEFT",
        inherited_from_process_seq="OP10",
    )
    assert text.startswith("继承 LEFT OP10 重量；")
