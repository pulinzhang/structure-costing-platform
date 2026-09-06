"""零件核价：多钢厂钢材联动价取最低吨价。"""

from decimal import Decimal
from types import SimpleNamespace

from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver


def test_pick_steel_price_takes_lowest_ton_price() -> None:
    rows = [
        SimpleNamespace(id=2, steel_mill="唐钢", final_price_per_ton=Decimal("4387")),
        SimpleNamespace(id=1, steel_mill="马钢", final_price_per_ton=Decimal("3742")),
        SimpleNamespace(id=3, steel_mill="首钢", final_price_per_ton=Decimal("4350")),
    ]
    picked = PriceResolver().pick_steel_price(rows)  # type: ignore[arg-type]
    assert picked is not None
    assert picked.steel_mill == "马钢"
    assert picked.final_price_per_ton == Decimal("3742")


def test_pick_steel_price_empty_or_unpriced() -> None:
    resolver = PriceResolver()
    assert resolver.pick_steel_price([]) is None
    assert (
        resolver.pick_steel_price(
            [SimpleNamespace(id=1, steel_mill="马钢", final_price_per_ton=None)]  # type: ignore[arg-type]
        )
        is None
    )
