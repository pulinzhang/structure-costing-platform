"""利废件材料：成品净重 × 废料单价，不查一事一议钢价。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.schemas.vo.stamping_part_cost_vo import StampingPartCostFailedItemVO
from app.services.costing.stamping_part_cost.calc.constants import AMOUNT_QUANTIZE, quantize
from app.services.costing.stamping_part_cost.calc.fees.die import DieFeeLookup
from app.services.costing.stamping_part_cost.calc.fees.gauge import GaugeFeeLookup
from app.services.costing.stamping_part_cost.calc.fees.process import ProcessFeeLookup
from app.services.costing.stamping_part_cost.calc.part_calculator import (
    PartCostCalculator,
    part_snapshot,
)


class _BoomSteel:
    def find_steel_prices(self, db: object, **kwargs: object) -> list[object]:
        raise AssertionError("利废件不应查钢材联动价")

    def pick_steel_price(self, rows: list[object]) -> object | None:
        raise AssertionError("利废件不应选钢材联动价")


class _ZeroProcess:
    def lookup(self, db: object, **kwargs: object) -> ProcessFeeLookup:
        return ProcessFeeLookup(process_fee_id=1, process_fee_amount=Decimal("0"))


class _ZeroDie:
    def lookup(self, db: object, **kwargs: object) -> DieFeeLookup:
        return DieFeeLookup(die_fee_id=None, die_fee_amount=Decimal("0"))


class _ZeroGauge:
    def lookup(self, db: object, **kwargs: object) -> GaugeFeeLookup:
        return GaugeFeeLookup(gauge_fee_id=None, gauge_fee_amount=Decimal("0"))


def _calculator() -> PartCostCalculator:
    return PartCostCalculator(
        price_resolver=_BoomSteel(),  # type: ignore[arg-type]
        process_fee_resolver=_ZeroProcess(),  # type: ignore[arg-type]
        die_fee_resolver=_ZeroDie(),  # type: ignore[arg-type]
        gauge_fee_resolver=_ZeroGauge(),  # type: ignore[arg-type]
    )


def test_offal_nested_is_net_weight_times_scrap() -> None:
    part = SimpleNamespace(
        part_number="502007709AA",
        part_name="侧围利废件",
        material="DC56D+Z",
        location="芜湖",
        vehicle_model="T13J",
        is_offal_nested=True,
        has_swing_shear=False,
        offal_source="侧围",
        sheet_length=None,
        sheet_width=None,
        thickness=Decimal("0.65"),
        part_weight=Decimal("0.246"),
        parts_per_sheet=None,
        stamping_supplier="振华",
    )
    scrap_ton = Decimal("2200")
    result = _calculator().calc_part_cost(
        db=None,  # type: ignore[arg-type]
        part=part,  # type: ignore[arg-type]
        year=2026,
        month=1,
        supplier="振华",
        scrap=SimpleNamespace(id=88),  # type: ignore[arg-type]
        scrap_ton_price=scrap_ton,
        density=Decimal("7.85"),
        loss_rate=Decimal("0.003"),
        recovery_rate=Decimal("0.97"),
        finance_rate=Decimal("0.02"),
        management_rate=Decimal("0.02"),
        warehouse_packaging_rate=Decimal("0.01"),
        pretax_profit_rate=Decimal("0.02"),
    )
    assert not isinstance(result, StampingPartCostFailedItemVO)
    assert result.steel_price_id is None
    assert result.steel_mill is None
    assert result.steel_ton_price == scrap_ton
    assert result.blank_weight_kg == Decimal("0.246")
    assert result.finished_total_kg == Decimal("0.246")
    assert result.scrap_weight_kg == Decimal("0")
    assert result.material_utilization_pct == Decimal("100.00")
    expected = quantize(Decimal("0.246") * scrap_ton / Decimal("1000"), AMOUNT_QUANTIZE)
    assert result.material_amount_sheet == expected
    assert result.loss_scrap_deduction == Decimal("0.000000")
    assert result.process_scrap_deduction == Decimal("0.000000")
    assert result.material_net_per_part == expected


def test_offal_nested_requires_part_weight() -> None:
    part = SimpleNamespace(
        part_number="502007709AA",
        part_name="侧围利废件",
        material="DC56D+Z",
        location="芜湖",
        vehicle_model="T13J",
        is_offal_nested=True,
        has_swing_shear=False,
        offal_source="侧围",
        sheet_length=None,
        sheet_width=None,
        thickness=None,
        part_weight=None,
        parts_per_sheet=None,
        stamping_supplier="振华",
    )
    result = _calculator().calc_part_cost(
        db=None,  # type: ignore[arg-type]
        part=part,  # type: ignore[arg-type]
        year=2026,
        month=1,
        supplier="振华",
        scrap=SimpleNamespace(id=88),  # type: ignore[arg-type]
        scrap_ton_price=Decimal("2200"),
        density=Decimal("7.85"),
        loss_rate=Decimal("0.003"),
        recovery_rate=Decimal("0.97"),
        finance_rate=Decimal("0.02"),
        management_rate=Decimal("0.02"),
        warehouse_packaging_rate=Decimal("0.01"),
        pretax_profit_rate=Decimal("0.02"),
    )
    assert isinstance(result, StampingPartCostFailedItemVO)
    assert "成品净重" in result.reason


def test_normal_part_still_requires_steel_price() -> None:
    part = SimpleNamespace(
        part_number="502008024AA",
        part_name="普通件",
        material="DC04",
        location="芜湖",
        vehicle_model="T13J",
        is_offal_nested=False,
        has_swing_shear=False,
        offal_source=None,
        sheet_length=Decimal("1080"),
        sheet_width=Decimal("465"),
        thickness=Decimal("0.7"),
        part_weight=Decimal("0.666"),
        parts_per_sheet=2,
        stamping_supplier="振华",
    )

    class _EmptySteel:
        def find_steel_prices(self, db: object, **kwargs: object) -> list[object]:
            return []

        def pick_steel_price(self, rows: list[object]) -> object | None:
            return None

    calculator = PartCostCalculator(
        price_resolver=_EmptySteel(),  # type: ignore[arg-type]
        process_fee_resolver=_ZeroProcess(),  # type: ignore[arg-type]
        die_fee_resolver=_ZeroDie(),  # type: ignore[arg-type]
        gauge_fee_resolver=_ZeroGauge(),  # type: ignore[arg-type]
    )
    result = calculator.calc_part_cost(
        db=None,  # type: ignore[arg-type]
        part=part,  # type: ignore[arg-type]
        year=2026,
        month=1,
        supplier="振华",
        scrap=SimpleNamespace(id=1),  # type: ignore[arg-type]
        scrap_ton_price=Decimal("2160.34"),
        density=Decimal("7.85"),
        loss_rate=Decimal("0.003"),
        recovery_rate=Decimal("0.97"),
        finance_rate=Decimal("0.02"),
        management_rate=Decimal("0.02"),
        warehouse_packaging_rate=Decimal("0.01"),
        pretax_profit_rate=Decimal("0.02"),
    )
    assert isinstance(result, StampingPartCostFailedItemVO)
    assert "没对上钢材联动价" in result.reason


def test_part_snapshot_writes_offal_onto_monthly_result() -> None:
    """结果表按月保存是否利废 / 利用哪类废料，不跟零件主表事后改动绑死。"""
    part = SimpleNamespace(
        id=11,
        seq_no=3,
        part_number="502007709AA",
        part_name="侧围利废件",
        material="DC56D+Z",
        thickness=Decimal("0.65"),
        part_weight=Decimal("0.246"),
        sheet_length=None,
        sheet_width=None,
        parts_per_sheet=None,
        sheet_type="方料",
        is_offal_nested=True,
        has_swing_shear=False,
        offal_source="侧围",
        die_type=None,
        process_method=None,
        automation=None,
        remark=None,
        sketch_url=None,
        excel_filename=None,
        excel_sheet_name=None,
        excel_row=None,
        excel_part_col=None,
    )
    snap = part_snapshot(part)  # type: ignore[arg-type]
    assert snap.is_offal_nested is True
    assert snap.offal_source == "侧围"
