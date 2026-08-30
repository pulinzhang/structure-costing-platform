"""冲压零件核价：模具费/检具费进直接成本。"""

from decimal import Decimal

from app.services.costing.stamping_part_cost.calc.constants import compute_finished_cost_stack
from app.services.costing.stamping_part_cost.calc.tooling_fees import gauge_fee_yuan_per_part


def test_gauge_fee_wan_over_wan_units_is_yuan_per_part() -> None:
    assert gauge_fee_yuan_per_part(Decimal("0.8"), Decimal("10")) == Decimal("0.080000")
    assert gauge_fee_yuan_per_part(Decimal("0.8"), Decimal("0")) == Decimal("0")


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
