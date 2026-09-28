"""同一年月、基地、牌号只能有一个中标钢厂；参考规格料厚不能超过车身件上限。"""

from decimal import Decimal

import pytest

from app.exceptions import BusinessException
from app.services.yishiyiyi.base_price.gate import (
    AwardLine,
    reject_invalid_base_price_award,
    reject_processing_fee_over_limit,
)

_LIMIT = Decimal("3.00")


def _line(
    *,
    steel_mill: str = "邯钢",
    location: str = "芜湖",
    grade: str = "DC51D+Z",
    thick: str | None = "1.00",
    width: str | None = "1250",
    excel_row: int | None = 6,
) -> AwardLine:
    return AwardLine(
        location=location,
        grade=grade,
        steel_mill=steel_mill,
        thick=None if thick is None else Decimal(thick),
        width=None if width is None else Decimal(width),
        excel_row=excel_row,
    )


def _accept(incoming: list[AwardLine], existing: list[AwardLine] | None = None) -> None:
    reject_invalid_base_price_award(incoming, existing or [], max_thickness=_LIMIT)


def test_same_mill_is_accepted_when_already_stored() -> None:
    _accept([_line()], [_line(excel_row=None)])


def test_same_mill_with_another_reference_thickness_is_accepted() -> None:
    _accept([_line(thick="1.20")], [_line(thick="1.00", excel_row=None)])


def test_other_location_may_use_another_mill() -> None:
    _accept(
        [_line(location="青岛", steel_mill="山钢")],
        [_line(location="芜湖", excel_row=None)],
    )


def test_second_mill_in_the_same_batch_is_rejected() -> None:
    with pytest.raises(BusinessException, match="只能有一个中标钢厂"):
        reject_invalid_base_price_award(
            [_line(steel_mill="邯钢"), _line(steel_mill="宝钢", excel_row=7)],
            [],
            max_thickness=_LIMIT,
        )


def test_second_mill_against_stored_row_is_rejected() -> None:
    with pytest.raises(BusinessException, match="库里已是邯钢"):
        reject_invalid_base_price_award(
            [_line(steel_mill="宝钢")],
            [_line(steel_mill="邯钢", excel_row=None)],
            max_thickness=_LIMIT,
        )


def test_empty_reference_thickness_is_rejected() -> None:
    with pytest.raises(BusinessException, match="参考规格的厚度是空的"):
        reject_invalid_base_price_award(
            [_line(thick=None)],
            [],
            max_thickness=_LIMIT,
        )


def test_empty_reference_width_is_rejected() -> None:
    with pytest.raises(BusinessException, match="参考规格的宽度是空的"):
        reject_invalid_base_price_award(
            [_line(width=None)],
            [],
            max_thickness=_LIMIT,
        )


def test_published_reference_specs_at_or_under_3mm_are_accepted() -> None:
    _accept(
        [
            _line(thick="1.0", width="1250"),
            _line(thick="0.8", width="1250"),
            _line(thick="1.2", width="1500"),
            _line(thick="3.0", width="1250"),
        ]
    )


def test_thickness_above_configured_limit_is_rejected() -> None:
    with pytest.raises(BusinessException, match="车身件料厚上限 3.00 mm"):
        reject_invalid_base_price_award(
            [_line(thick="3.01", width="1250")],
            [],
            max_thickness=_LIMIT,
        )


def _fee(amount: str) -> AwardLine:
    return AwardLine(
        location="芜湖",
        grade="DC51D+Z",
        steel_mill="邯钢",
        thick=Decimal("1"),
        processing_fee=Decimal(amount),
        excel_row=6,
    )


def test_processing_fee_at_limit_is_accepted() -> None:
    reject_processing_fee_over_limit([_fee("120")], limit=Decimal("120"))


def test_processing_fee_over_limit_is_rejected() -> None:
    with pytest.raises(BusinessException, match="设置上限是 120.00"):
        reject_processing_fee_over_limit([_fee("121")], limit=Decimal("120"))


def test_raised_thickness_limit_accepts_a_thicker_spec() -> None:
    reject_invalid_base_price_award(
        [_line(thick="3.20", width="1250")],
        [],
        max_thickness=Decimal("3.20"),
    )
