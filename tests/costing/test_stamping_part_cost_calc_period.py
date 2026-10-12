"""冲压零件价格计算：按零件有效期命中计算月，不靠版本。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions.base import BusinessException
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.services.costing.stamping_part_cost.calc.orchestrator.prep import prepare_calc_run
from app.services.costing.stamping_part_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.stamping_part_cost.calc.orchestrator.rates import PartCostCalcRates


def _rates() -> PartCostCalcRates:
    return PartCostCalcRates(
        density=Decimal("7.85"),
        loss_rate=Decimal("0.003"),
        recovery_rate=Decimal("0.97"),
        finance_rate=Decimal("0.01"),
        management_rate=Decimal("0.01"),
        warehouse_packaging_rate=Decimal("0.01"),
        pretax_profit_rate=Decimal("0.01"),
        swing_shear_fee_per_ton=Decimal("0"),
    )


def _ready() -> SimpleNamespace:
    return SimpleNamespace(
        can_calculate=True,
        part_count=1,
        steel_price_count=1,
        scrap_price_count=1,
        process_fee_count=1,
        die_fee_count=0,
        gauge_fee_count=0,
    )


@patch("app.services.costing.stamping_part_cost.calc.orchestrator.prep.VehicleModelService")
@patch(
    "app.services.costing.stamping_part_cost.calc.orchestrator.prep.collect_calc_ready",
    return_value=_ready(),
)
@patch(
    "app.services.costing.stamping_part_cost.calc.orchestrator.prep.load_part_cost_calc_rates",
    return_value=_rates(),
)
def test_prep_lists_parts_by_as_of_month_without_version(
    _rates_mock: MagicMock,
    _ready_mock: MagicMock,
    vehicle_cls: MagicMock,
) -> None:
    vehicle_cls.return_value.require_introducible.return_value = ("青岛", "T13J")
    deps = MagicMock()
    deps.price_resolver.find_scrap_price.return_value = SimpleNamespace(
        id=1, net_price=Decimal("1"), location="青岛"
    )
    deps.part_repo.list_with_processes.return_value = [SimpleNamespace(id=1)]

    prepare_calc_run(
        MagicMock(),
        deps,
        StampingPartCostCalcDTO(
            year=2026,
            month=7,
            location="青岛",
            vehicle_model="T13J",
            version="V9",
        ),
        ProgressNotifier(),
    )

    kwargs = deps.part_repo.list_with_processes.call_args.kwargs
    assert kwargs["location"] == "青岛"
    assert kwargs["vehicle_model"] == "T13J"
    assert kwargs["as_of_year"] == 2026
    assert kwargs["as_of_month"] == 7
    assert "version" not in kwargs
    assert "overlap_year" not in kwargs


@patch("app.services.costing.stamping_part_cost.calc.orchestrator.prep.VehicleModelService")
@patch(
    "app.services.costing.stamping_part_cost.calc.orchestrator.prep.collect_calc_ready",
    return_value=_ready(),
)
@patch(
    "app.services.costing.stamping_part_cost.calc.orchestrator.prep.load_part_cost_calc_rates",
    return_value=_rates(),
)
def test_prep_empty_as_of_month_raises(
    _rates_mock: MagicMock,
    _ready_mock: MagicMock,
    vehicle_cls: MagicMock,
) -> None:
    vehicle_cls.return_value.require_introducible.return_value = ("青岛", "T13J")
    deps = MagicMock()
    deps.price_resolver.find_scrap_price.return_value = SimpleNamespace(
        id=1, net_price=Decimal("1"), location="青岛"
    )
    deps.part_repo.list_with_processes.return_value = []

    with pytest.raises(BusinessException, match="2026年07月没有有效期内的冲压零件"):
        prepare_calc_run(
            MagicMock(),
            deps,
            StampingPartCostCalcDTO(
                year=2026,
                month=7,
                location="青岛",
                vehicle_model="T13J",
            ),
            ProgressNotifier(),
        )
