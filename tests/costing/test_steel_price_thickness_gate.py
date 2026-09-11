"""钢价计算：适用却未命中厚度政策时拒绝启动/落库。"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions.base import BusinessException
from app.schemas.dto.steel_price_dto import SteelPriceCalcDTO
from app.services.costing.steel_price.calc.coverage import (
    raise_if_thickness_gaps,
    thickness_gap_labels,
)
from app.services.costing.steel_price.calc.models import CalcRow
from app.services.costing.steel_price.calc.orchestrator.orchestrator import (
    SteelPriceCalcOrchestrator,
)


def _row(*, mill: str = "马钢", applicable: bool = True) -> CalcRow:
    return CalcRow(
        year=2026,
        month=2,
        location="芜湖",
        grade="DC01",
        thickness=Decimal("0.6"),
        steel_mill=mill,
        thickness_applicable=applicable,
    )


def test_thickness_gap_labels_only_applicable_miss() -> None:
    miss = _row()
    skip = _row(mill="鞍神", applicable=False)
    hit = _row()
    hit.thickness_policy_id = 9
    assert thickness_gap_labels([miss, skip, hit]) == ["DC01@0.6000/马钢"]


def test_raise_if_thickness_gaps_blocks_applicable_miss() -> None:
    with pytest.raises(BusinessException, match="须补齐后再计算：DC01@0.6000/马钢"):
        raise_if_thickness_gaps([_row()])


def test_raise_if_thickness_gaps_allows_mill_without_block() -> None:
    raise_if_thickness_gaps([_row(applicable=False)])


@patch(
    "app.services.costing.steel_price.calc.orchestrator.orchestrator.assert_steel_calc_thickness"
)
@patch("app.services.costing.steel_price.calc.orchestrator.orchestrator.LocationService")
def test_start_calc_refuses_before_period_lock(
    location_cls: MagicMock,
    assert_thickness: MagicMock,
) -> None:
    location_cls.return_value.require_enabled.return_value = "芜湖"
    assert_thickness.side_effect = BusinessException(
        "厚度政策匹配失败 1 项，须补齐后再计算：DC01@0.6000/马钢"
    )
    orchestrator = SteelPriceCalcOrchestrator(deps=MagicMock())
    orchestrator.begin_processing = MagicMock()
    user = MagicMock()
    user.id = 1

    with pytest.raises(BusinessException, match="须补齐后再计算"):
        orchestrator.start_calc(
            MagicMock(),
            SteelPriceCalcDTO(year=2026, month=2, location="芜湖"),
            user,
        )

    orchestrator.begin_processing.assert_not_called()
