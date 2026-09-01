"""冲压零件核价黄金样例：芜湖 T13J 502008024AA + 2026-01 废料 / 钢材。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session, selectinload

from app.models.stamping import StampingPart
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostFailedItemVO
from app.services.costing.stamping_part_cost.calc.constants import compute_finished_cost_stack
from app.services.costing.stamping_part_cost.calc.fees.die import DieFeeResolver
from app.services.costing.stamping_part_cost.calc.fees.gauge import GaugeFeeResolver
from app.services.costing.stamping_part_cost.calc.part_calculator import PartCostCalculator
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.steel_price.calc.models import (
    MaterialThicknessRow,
    SteelPriceCalcRequest,
)
from app.services.costing.steel_price.calc.steps.apply_adjustments import AdjustmentApplier
from app.services.costing.steel_price.calc.steps.enrich_base_price import BasePriceEnricher
from app.services.settings.system.settings_service import SettingsService

YEAR = 2026
MONTH = 1
LOCATION = "芜湖"
VEHICLE_MODEL = "T13J"
VERSION = "V3"
PART_NUMBER = "502008024AA"


class _SteelFromPeriod:
    """主库尚无 2026-01 steel_prices 落库，用同期基价+政策算出的吨价注入。"""

    def __init__(self, steel_mill: str, final_price_per_ton: Decimal) -> None:
        self._steel_mill = steel_mill
        self._final_price_per_ton = final_price_per_ton

    def find_steel_prices(self, db: object, **kwargs: object) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                id=1,
                steel_mill=self._steel_mill,
                final_price_per_ton=self._final_price_per_ton,
            )
        ]

    def pick_steel_price(self, rows: list[SimpleNamespace]) -> SimpleNamespace | None:
        return rows[0] if rows else None


def _load_part(db: Session) -> StampingPart:
    part = (
        db.query(StampingPart)
        .options(selectinload(StampingPart.processes))
        .filter(
            StampingPart.location == LOCATION,
            StampingPart.vehicle_model == VEHICLE_MODEL,
            StampingPart.version == VERSION,
            StampingPart.part_number == PART_NUMBER,
        )
        .one_or_none()
    )
    if part is None:
        pytest.skip(f"无零件: {LOCATION}/{VEHICLE_MODEL}/{VERSION}/{PART_NUMBER}")
    return part


def _steel_ton_from_2026_01(db: Session, *, grade: str, thickness: Decimal) -> tuple[str, Decimal]:
    request = SteelPriceCalcRequest(year=YEAR, month=MONTH, location=LOCATION)
    rows, no_base_count, details = BasePriceEnricher().enrich(
        db,
        request,
        [MaterialThicknessRow(location=LOCATION, material=grade, thickness=thickness)],
    )
    if no_base_count or not rows:
        pytest.skip(f"无 2026-01 基价: {LOCATION}/{grade} {details}")
    applier = AdjustmentApplier()
    policies = applier.load_policies(db, request)
    rows = applier.apply_thickness(db, rows, policies)
    rows = applier.apply_width(rows, policies)
    priced = []
    for index, row in enumerate(rows, start=1):
        payload = row.to_persist_payload(calc_batch_id="gold-2026-01", formula_version="test")
        priced.append(
            SimpleNamespace(
                id=index,
                steel_mill=row.steel_mill,
                final_price_per_ton=payload.final_price_per_ton,
            )
        )
    picked = PriceResolver().pick_steel_price(priced)  # type: ignore[arg-type]
    if picked is None:
        pytest.skip(f"2026-01 {grade}@{thickness} 无有效吨价")
    mill = (picked.steel_mill or "").strip()
    return mill, Decimal(str(picked.final_price_per_ton))


@pytest.mark.integration
def test_stamping_part_cost_golden_wuhu_2026_01(db_session: Session) -> None:
    """
    芜湖 T13J V3 / 502008024AA：料片 1080×465×0.7、可制 2、单重 0.666。
    钢材：2026-01 镀锌大类多钢厂取最低吨价 VAMA 4269（基价4049+厚加减100+加工费120）。
    废料：芜湖 2026-01 净价；加工费：2026 年度确认单价 1.508。
    """
    part = _load_part(db_session)
    thickness = part.thickness
    material = (part.material or "").strip()
    if thickness is None or not material:
        pytest.skip("零件缺材质或料厚")

    mill, steel_ton = _steel_ton_from_2026_01(
        db_session,
        grade=material,
        thickness=Decimal(str(thickness)),
    )
    assert mill == "VAMA"
    assert steel_ton == Decimal("4269.00")

    scrap = PriceResolver().find_scrap_price(
        db_session,
        location=LOCATION,
        year=YEAR,
        month=MONTH,
    )
    if scrap is None:
        pytest.skip(f"无废料价: {LOCATION}/{YEAR}-{MONTH:02d}")
    assert Decimal(str(scrap.net_price)) == Decimal("2160.34")

    settings_svc = SettingsService()
    calculator = PartCostCalculator(
        price_resolver=_SteelFromPeriod(mill, steel_ton),  # type: ignore[arg-type]
    )
    result = calculator.calc_part_cost(
        db_session,
        part=part,
        year=YEAR,
        month=MONTH,
        supplier=part.stamping_supplier or "",
        scrap=scrap,
        scrap_ton_price=Decimal(str(scrap.net_price)),
        density=settings_svc.get_steel_density(db_session),
        loss_rate=settings_svc.get_material_loss_rate(db_session),
        recovery_rate=settings_svc.get_scrap_recovery_rate(db_session),
        finance_rate=settings_svc.get_finished_finance_rate(db_session),
        management_rate=settings_svc.get_finished_management_rate(db_session),
        warehouse_packaging_rate=settings_svc.get_finished_warehouse_packaging_rate(db_session),
        pretax_profit_rate=settings_svc.get_finished_pretax_profit_rate(db_session),
    )
    assert not isinstance(result, StampingPartCostFailedItemVO)
    assert result.process_fee_amount == Decimal("1.508")
    assert result.blank_weight_kg == Decimal("1.3797945")
    assert result.scrap_weight_kg == Decimal("0.7137945")
    assert result.material_utilization_pct == Decimal("48.27")
    assert result.material_amount_sheet == Decimal("5.908014")
    assert result.loss_scrap_deduction == Decimal("0.008674")
    assert result.process_scrap_deduction == Decimal("1.495778")
    assert result.material_net_per_part == Decimal("4.403562")
    die = DieFeeResolver().lookup(
        db_session,
        year=YEAR,
        location=LOCATION,
        vehicle_model=part.vehicle_model,
        part_number=part.part_number,
    )
    gauge = GaugeFeeResolver().lookup(
        db_session,
        location=LOCATION,
        vehicle_model=part.vehicle_model,
        part_number=part.part_number,
    )
    assert result.die_fee_amount == die.die_fee_amount
    assert result.gauge_fee_amount == gauge.gauge_fee_amount
    finance_rate = settings_svc.get_finished_finance_rate(db_session)
    management_rate = settings_svc.get_finished_management_rate(db_session)
    warehouse_packaging_rate = settings_svc.get_finished_warehouse_packaging_rate(db_session)
    pretax_profit_rate = settings_svc.get_finished_pretax_profit_rate(db_session)
    (
        expected_direct,
        expected_finance,
        _expected_management,
        expected_warehouse,
        _expected_pretax,
        expected_unit,
    ) = compute_finished_cost_stack(
        material_net_per_part=Decimal("4.403562"),
        process_fee_amount=Decimal("1.508"),
        die_fee_amount=die.die_fee_amount,
        gauge_fee_amount=gauge.gauge_fee_amount,
        finance_rate=finance_rate,
        management_rate=management_rate,
        warehouse_packaging_rate=warehouse_packaging_rate,
        pretax_profit_rate=pretax_profit_rate,
    )
    assert result.direct_cost == expected_direct
    assert result.finished_finance_fee == expected_finance
    assert result.finished_warehouse_packaging_fee == expected_warehouse
    assert result.unit_cost == expected_unit
