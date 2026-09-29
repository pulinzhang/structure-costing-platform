"""单价+加工费相对上月超过 ±800 元/吨则整批拒绝。"""

from decimal import Decimal

import pytest

from app.common.period import previous_month
from app.exceptions import BusinessException
from app.services.yishiyiyi.base_price.gate import (
    AwardLine,
    reject_excessive_month_moves,
)


def _line(
    *,
    base_price: str,
    processing_fee: str,
    location: str = "芜湖",
    steel_mill: str = "邯钢",
    excel_row: int | None = 6,
) -> AwardLine:
    return AwardLine(
        location=location,
        steel_mill=steel_mill,
        grade="DC51D+Z",
        thick=Decimal("1.00"),
        width=Decimal("1250.00"),
        base_price=Decimal(base_price),
        processing_fee=Decimal(processing_fee),
        excel_row=excel_row,
    )


def test_previous_month_wraps_january() -> None:
    assert previous_month(2026, 7) == (2026, 6)
    assert previous_month(2026, 1) == (2025, 12)


_LIMIT = Decimal("300")


def test_move_of_limit_is_accepted() -> None:
    previous = [_line(base_price="3969", processing_fee="120")]
    incoming = [_line(base_price="4269", processing_fee="120")]
    reject_excessive_month_moves(incoming, previous, limit=_LIMIT)


def test_move_over_limit_is_rejected() -> None:
    previous = [_line(base_price="3969", processing_fee="120")]
    incoming = [_line(base_price="3969", processing_fee="3950")]
    with pytest.raises(BusinessException, match=r"±300\.00"):
        reject_excessive_month_moves(incoming, previous, limit=_LIMIT)


def test_raised_limit_accepts_a_larger_move() -> None:
    previous = [_line(base_price="3969", processing_fee="120")]
    incoming = [_line(base_price="4769", processing_fee="120")]
    reject_excessive_month_moves(incoming, previous, limit=Decimal("800"))


def test_drop_over_limit_is_rejected() -> None:
    previous = [_line(base_price="3969", processing_fee="120")]
    incoming = [_line(base_price="3000", processing_fee="120")]
    with pytest.raises(BusinessException, match="变动 -969.00"):
        reject_excessive_month_moves(incoming, previous, limit=_LIMIT)


def test_no_previous_month_is_accepted() -> None:
    incoming = [_line(base_price="3969", processing_fee="3950")]
    reject_excessive_month_moves(incoming, [], limit=_LIMIT)


def test_mill_change_uses_the_only_previous_spec_line() -> None:
    previous = [_line(base_price="3969", processing_fee="120", steel_mill="马钢")]
    incoming = [_line(base_price="3969", processing_fee="3950", steel_mill="邯钢")]
    with pytest.raises(BusinessException, match="上月同基地 4089.00（马钢）"):
        reject_excessive_month_moves(incoming, previous, limit=_LIMIT)


def test_other_location_is_not_the_baseline() -> None:
    previous = [_line(base_price="3969", processing_fee="120", location="芜湖")]
    incoming = [_line(base_price="3969", processing_fee="3950", location="青岛")]
    reject_excessive_month_moves(incoming, previous, limit=_LIMIT)


def test_same_location_still_rejects_when_other_location_is_calm() -> None:
    previous = [
        _line(base_price="3969", processing_fee="120", location="芜湖"),
        _line(base_price="3950", processing_fee="120", location="青岛"),
    ]
    incoming = [
        _line(base_price="3969", processing_fee="3950", location="芜湖"),
        _line(base_price="4000", processing_fee="120", location="青岛"),
    ]
    with pytest.raises(BusinessException, match="芜湖") as caught:
        reject_excessive_month_moves(incoming, previous, limit=_LIMIT)
    assert "青岛" not in str(caught.value)


def test_ambiguous_previous_mills_are_not_guessed() -> None:
    previous = [
        _line(base_price="3969", processing_fee="120", steel_mill="马钢"),
        _line(base_price="3900", processing_fee="120", steel_mill="山钢"),
    ]
    incoming = [_line(base_price="3969", processing_fee="3950", steel_mill="邯钢")]
    reject_excessive_month_moves(incoming, previous, limit=_LIMIT)
