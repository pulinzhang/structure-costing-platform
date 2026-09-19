"""冲压零件核价：模具费 / 检具费按种类分公式。"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.services.costing.stamping_part_cost.calc.constants import compute_finished_cost_stack
from app.services.costing.stamping_part_cost.calc.fees.die import DieFeeResolver
from app.services.costing.stamping_part_cost.calc.fees.gauge import (
    GaugeFeeResolver,
    gauge_fee_yuan_per_part,
)


def test_gauge_fee_wan_over_wan_units_is_yuan_per_part() -> None:
    assert gauge_fee_yuan_per_part(Decimal("0.8"), Decimal("10")) == Decimal("0.080000")
    assert gauge_fee_yuan_per_part(Decimal("0.8"), Decimal("0")) == Decimal("0")


def test_die_fee_uses_final_yuan_per_part_without_reallocating() -> None:
    """年度模具费最终价已是元/件，不得再按检具费的万元÷万台重摊。"""
    row = SimpleNamespace(id=11, final_die_fee=Decimal("1.234500"))
    repo = SimpleNamespace(
        get_by_year_location_vehicle_part=lambda db, **kwargs: row,
    )
    with patch(
        "app.services.costing.stamping_part_cost.calc.fees.die.LocationService"
    ) as location_service:
        location_service.return_value.expand_for_query.return_value = ["芜湖基地"]
        lookup = DieFeeResolver(die_fee_repo=repo).lookup(  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            year=2026,
            location="芜湖基地",
            vehicle_model="T13J",
            part_number="502008024AA",
        )
    assert lookup.die_fee_id == 11
    assert lookup.die_fee_amount == Decimal("1.234500")


def test_die_fee_matches_location_alias() -> None:
    row = SimpleNamespace(id=3, final_die_fee=Decimal("0.500000"))

    def get_row(db: object, *, location: str, **kwargs: object) -> SimpleNamespace | None:
        if location == "芜湖":
            return row
        return None

    repo = SimpleNamespace(get_by_year_location_vehicle_part=get_row)
    with patch(
        "app.services.costing.stamping_part_cost.calc.fees.die.LocationService"
    ) as location_service:
        location_service.return_value.expand_for_query.return_value = ["芜湖基地", "芜湖"]
        lookup = DieFeeResolver(die_fee_repo=repo).lookup(  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            year=2026,
            location="芜湖基地",
            vehicle_model="T13J",
            part_number="502008024AA",
        )
    assert lookup.die_fee_id == 3
    assert lookup.die_fee_amount == Decimal("0.500000")


def test_gauge_fee_allocates_wan_over_wan_units() -> None:
    row = SimpleNamespace(id=7, gauge_fee=Decimal("0.8"), allocation_qty=Decimal("10"))
    repo = SimpleNamespace(get_effective_by_part=lambda db, **kwargs: row)
    with patch(
        "app.services.costing.stamping_part_cost.calc.fees.gauge.LocationService"
    ) as location_service:
        location_service.return_value.expand_for_query.return_value = ["芜湖"]
        lookup = GaugeFeeResolver(gauge_fee_repo=repo).lookup(  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            location="芜湖",
            vehicle_model="T13J",
            part_number="502008024AA",
        )
    assert lookup.gauge_fee_id == 7
    assert lookup.gauge_fee_amount == Decimal("0.080000")


def test_direct_cost_includes_die_and_gauge_fees() -> None:
    direct, finance, management, warehouse, pretax, unit = compute_finished_cost_stack(
        material_net_per_part=Decimal("4.265168"),
        process_fee_amount=Decimal("1.508"),
        die_fee_amount=Decimal("0.120000"),
        gauge_fee_amount=Decimal("0.080000"),
        finance_rate=Decimal("0.02"),
        management_rate=Decimal("0.03"),
        warehouse_packaging_rate=Decimal("0.01"),
        pretax_profit_rate=Decimal("0.02"),
    )
    assert direct == Decimal("5.973168")
    assert finance == Decimal("0.119463")
    assert management == Decimal("0.179195")
    assert warehouse == Decimal("0.059732")
    assert pretax == Decimal("0.119463")
    assert unit == Decimal("6.451021")
