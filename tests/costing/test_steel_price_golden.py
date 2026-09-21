"""钢材联动黄金样例：芜湖 2026-01 马钢 DC01 厚度阶梯 + 吨价加总。"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.services.costing.steel_price.calc.models import (
    MaterialThicknessRow,
    SteelPriceCalcRequest,
)
from app.services.costing.steel_price.calc.steps.apply_adjustments import AdjustmentApplier
from app.services.costing.steel_price.calc.steps.enrich_base_price import BasePriceEnricher
from app.services.costing.steel_price.pricing import compute_final_price

YEAR = 2026
MONTH = 1
LOCATION = "芜湖"
GRADE = "DC01"
THICKNESS = Decimal("0.7")
STEEL_MILL = "马钢"


@pytest.mark.integration
def test_steel_price_golden_wuhu_2026_01_magang_dc01(db_session: Session) -> None:
    """
    芜湖 2026-01 马钢 DC01 厚 0.7（T13J 常见料厚）。
    基价 3742 + 原卷加工费 120；厚度命中 [0.7, 0.8) +160；宽度本期不应用。
    final = 3742 + 160 + 0 + 0 + 120 + 0 = 4022。
    """
    request = SteelPriceCalcRequest(year=YEAR, month=MONTH, location=LOCATION)
    rows, no_base_count, details = BasePriceEnricher().enrich(
        db_session,
        request,
        [
            MaterialThicknessRow(
                location=LOCATION,
                material=GRADE,
                thickness=THICKNESS,
            )
        ],
    )
    if no_base_count or not rows:
        pytest.skip(f"无 2026-01 基价: {LOCATION}/{GRADE} {details}")

    applier = AdjustmentApplier()
    policies = applier.load_policies(db_session, request)
    if not policies:
        pytest.skip(f"无加减价政策: {YEAR}-{MONTH:02d}")
    rows = applier.apply_thickness(db_session, rows, policies)
    rows = applier.apply_width(rows, policies)

    magang = [row for row in rows if (row.steel_mill or "").strip() == STEEL_MILL]
    if not magang:
        pytest.skip(f"无 {STEEL_MILL} 基价行: {LOCATION}/{GRADE}/{YEAR}-{MONTH:02d}")
    row = magang[0]

    assert row.base_price == Decimal("3742.00")
    assert row.processing_fee == Decimal("120.00")
    assert row.thickness_adjustment == Decimal("160")
    assert row.width_adjustment == Decimal("0")
    assert row.zinc_adjustment == Decimal("0")
    assert row.match_status == "full_match"
    assert row.calc_status == "success"

    payload = row.to_persist_payload(calc_batch_id="gold-2026-01", formula_version="test")
    assert payload.final_price_per_ton == Decimal("4022.00")
    assert payload.final_price_per_ton == compute_final_price(
        base_price=Decimal("3742.00"),
        thickness_adjustment=Decimal("160"),
        width_adjustment=Decimal("0"),
        zinc_adjustment=Decimal("0"),
        processing_fee=Decimal("120.00"),
        other_adjustment=Decimal("0"),
    )


@pytest.mark.integration
def test_steel_price_golden_wuhu_2026_01_magang_hc180y_06(db_session: Session) -> None:
    """
    芜湖 2026-01 马钢 HC180Y 厚 0.6。
    基价表有该牌号则用牌号基价 3919，不回退 DC01 的 3742。
    厚度按大类政策命中 [0.6, 0.7) +200；宽度本期不应用。
    final = 3919 + 200 + 0 + 0 + 120 + 0 = 4239。
    """
    request = SteelPriceCalcRequest(year=YEAR, month=MONTH, location=LOCATION)
    rows, no_base_count, details = BasePriceEnricher().enrich(
        db_session,
        request,
        [
            MaterialThicknessRow(
                location=LOCATION,
                material="HC180Y",
                thickness=Decimal("0.6"),
            )
        ],
    )
    if no_base_count or not rows:
        pytest.skip(f"无 2026-01 基价: {LOCATION}/HC180Y {details}")

    applier = AdjustmentApplier()
    policies = applier.load_policies(db_session, request)
    if not policies:
        pytest.skip(f"无加减价政策: {YEAR}-{MONTH:02d}")
    rows = applier.apply_thickness(db_session, rows, policies)
    rows = applier.apply_width(rows, policies)

    magang = [row for row in rows if (row.steel_mill or "").strip() == STEEL_MILL]
    if not magang:
        pytest.skip(f"无 {STEEL_MILL} 基价行: {LOCATION}/HC180Y/{YEAR}-{MONTH:02d}")
    row = magang[0]

    assert row.base_price == Decimal("3919.00")
    assert row.processing_fee == Decimal("120.00")
    assert row.thickness_adjustment == Decimal("200")
    assert row.thickness_policy_id is not None
    assert row.width_adjustment == Decimal("0")
    assert row.match_status == "full_match"
    assert row.calc_status == "success"

    payload = row.to_persist_payload(calc_batch_id="gold-2026-01-hc180y", formula_version="test")
    assert payload.final_price_per_ton == Decimal("4239.00")
    assert payload.final_price_per_ton == compute_final_price(
        base_price=Decimal("3919.00"),
        thickness_adjustment=Decimal("200"),
        width_adjustment=Decimal("0"),
        zinc_adjustment=Decimal("0"),
        processing_fee=Decimal("120.00"),
        other_adjustment=Decimal("0"),
    )
