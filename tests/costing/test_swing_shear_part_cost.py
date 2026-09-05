"""摆剪件材料核算：钢价加上系统摆剪吨价，结果快照加了多少。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.schemas.vo.stamping_part_cost_vo import StampingPartCostFailedItemVO
from app.services.costing.stamping_part_cost.calc.constants import AMOUNT_QUANTIZE, quantize
from app.services.costing.stamping_part_cost.calc.fees.die import DieFeeLookup
from app.services.costing.stamping_part_cost.calc.fees.gauge import GaugeFeeLookup
from app.services.costing.stamping_part_cost.calc.fees.process import ProcessFeeLookup
from app.services.costing.stamping_part_cost.calc.part_calculator import PartCostCalculator


class _FixedSteel:
    def find_steel_prices(self, db: object, **kwargs: object) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=7, steel_mill="VAMA", final_price_per_ton=Decimal("4269.00"))]

    def pick_steel_price(self, rows: list[SimpleNamespace]) -> SimpleNamespace | None:
        return rows[0] if rows else None


class _ZeroProcess:
    def lookup(self, db: object, **kwargs: object) -> ProcessFeeLookup:
        return ProcessFeeLookup(process_fee_id=1, process_fee_amount=Decimal("0"))


class _ZeroDie:
    def lookup(self, db: object, **kwargs: object) -> DieFeeLookup:
        return DieFeeLookup(die_fee_id=None, die_fee_amount=Decimal("0"))


class _ZeroGauge:
    def lookup(self, db: object, **kwargs: object) -> GaugeFeeLookup:
        return GaugeFeeLookup(gauge_fee_id=None, gauge_fee_amount=Decimal("0"))


def _part(*, has_swing_shear: bool) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        seq_no=24,
        part_number="502018915AA",
        part_name="左C柱内板",
        material="HC180Y",
        location="青岛",
        vehicle_model="T2AA",
        version="V1",
        is_offal_nested=False,
        offal_source=None,
        has_swing_shear=has_swing_shear,
        sheet_length=Decimal("1150"),
        sheet_width=Decimal("810"),
        thickness=Decimal("0.7"),
        part_weight=Decimal("2.249"),
        parts_per_sheet=1,
        sheet_type="梯形",
        die_type="铸造模",
        process_method="双槽",
        automation="自动化",
        remark=None,
        sketch_url=None,
        excel_filename=None,
        excel_sheet_name=None,
        excel_row=None,
        excel_part_col=None,
        stamping_supplier="海众",
    )


def _calc(*, has_swing_shear: bool, fee: Decimal) -> object:
    calculator = PartCostCalculator(
        price_resolver=_FixedSteel(),  # type: ignore[arg-type]
        process_fee_resolver=_ZeroProcess(),  # type: ignore[arg-type]
        die_fee_resolver=_ZeroDie(),  # type: ignore[arg-type]
        gauge_fee_resolver=_ZeroGauge(),  # type: ignore[arg-type]
    )
    return calculator.calc_part_cost(
        db=None,  # type: ignore[arg-type]
        part=_part(has_swing_shear=has_swing_shear),  # type: ignore[arg-type]
        year=2026,
        month=8,
        supplier="海众",
        scrap=SimpleNamespace(id=3),  # type: ignore[arg-type]
        scrap_ton_price=Decimal("2000"),
        density=Decimal("7.85"),
        loss_rate=Decimal("0.003"),
        recovery_rate=Decimal("0.97"),
        finance_rate=Decimal("0.02"),
        management_rate=Decimal("0.02"),
        warehouse_packaging_rate=Decimal("0.01"),
        pretax_profit_rate=Decimal("0.02"),
        swing_shear_fee_per_ton=fee,
    )


def test_swing_shear_adds_setting_to_steel_price() -> None:
    baseline = _calc(has_swing_shear=False, fee=Decimal("150"))
    billed = _calc(has_swing_shear=True, fee=Decimal("150"))
    assert not isinstance(baseline, StampingPartCostFailedItemVO)
    assert not isinstance(billed, StampingPartCostFailedItemVO)
    assert baseline.steel_ton_price == Decimal("4269.00")
    assert billed.steel_ton_price == Decimal("4269.00")
    assert baseline.swing_shear_fee_per_ton == Decimal("0")
    assert billed.swing_shear_fee_per_ton == Decimal("150")
    extra = quantize(
        billed.blank_weight_kg * Decimal("150") / Decimal("1000") * Decimal("1.003"),
        AMOUNT_QUANTIZE,
    )
    assert billed.material_amount_sheet == quantize(
        baseline.material_amount_sheet + extra, AMOUNT_QUANTIZE
    )
