"""冲压加工费黄金样例：2026 芜湖现网零件（2026-01 核价期所用年度单价）。"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session, selectinload

from app.models.stamping import StampingPart
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.services.stamping.process_fee.calc.models import TonnageRateInfo
from app.services.stamping.process_fee.calc.part_calculator import PartFeeCalculator
from app.services.stamping.process_fee.fee_math import resolve_final_fee

YEAR = 2026
LOCATION = "芜湖"


def _load_part(
    db: Session,
    *,
    part_number: str,
    vehicle_model: str,
    version: str,
) -> StampingPart:
    part = (
        db.query(StampingPart)
        .options(selectinload(StampingPart.processes))
        .filter(
            StampingPart.location == LOCATION,
            StampingPart.vehicle_model == vehicle_model,
            StampingPart.version == version,
            StampingPart.part_number == part_number,
        )
        .one_or_none()
    )
    if part is None:
        pytest.skip(f"无零件: {LOCATION}/{vehicle_model}/{version}/{part_number}")
    return part


def _rate_map(db: Session) -> dict[int, TonnageRateInfo]:
    rates = StampingTonnagePriceRepository().list_by_location_year(db, LOCATION, YEAR)
    if not rates:
        pytest.skip(f"无冲次单价: {LOCATION}/{YEAR}")
    return {
        int(row.tonnage): TonnageRateInfo(
            price_per_stroke=Decimal(str(row.price_per_stroke)),
            tonnage_price_id=row.id,
        )
        for row in rates
    }


@pytest.mark.integration
def test_process_fee_golden_wuhu_2026_swing_shear(db_session: Session) -> None:
    """
    芜湖 T13J-BEV V3 / 502011828AA 左B柱内板：OP05 摆剪计 0。
    冲次单价取 2026 年芜湖表（2026-01 核价期）。
    """
    part = _load_part(
        db_session,
        part_number="502011828AA",
        vehicle_model="T13J-BEV",
        version="V3",
    )
    result = PartFeeCalculator().calc_part_fee(
        part,
        _rate_map(db_session),
        YEAR,
    )
    assert isinstance(result, tuple)
    total, process_count, items = result

    assert process_count == 6
    assert [item.process_seq for item in items] == [
        "OP05",
        "OP10",
        "OP20",
        "OP30",
        "OP40",
        "OP50",
    ]
    assert items[0].tonnage_source == "swing_shear"
    assert [item.line_fee for item in items] == [
        Decimal("0.000"),
        Decimal("1.667"),
        Decimal("0.713"),
        Decimal("1.283"),
        Decimal("0.713"),
        Decimal("0.713"),
    ]
    assert total == Decimal("5.089")
    assert resolve_final_fee(total, None) == Decimal("5.089")


@pytest.mark.integration
def test_process_fee_golden_wuhu_2026_half_ratio(db_session: Session) -> None:
    """
    芜湖 T13J V3 / 502008024AA 左侧围外板后部连接板：左右合并，费用比例 0.5。
    """
    part = _load_part(
        db_session,
        part_number="502008024AA",
        vehicle_model="T13J",
        version="V3",
    )
    result = PartFeeCalculator().calc_part_fee(
        part,
        _rate_map(db_session),
        YEAR,
    )
    assert isinstance(result, tuple)
    total, process_count, items = result

    assert process_count == 4
    assert [item.cost_ratio for item in items] == [
        Decimal("0.50"),
        Decimal("0.50"),
        Decimal("0.50"),
        Decimal("0.50"),
    ]
    assert [item.line_fee for item in items] == [
        Decimal("0.513"),
        Decimal("0.357"),
        Decimal("0.357"),
        Decimal("0.282"),
    ]
    assert total == Decimal("1.508")
    assert resolve_final_fee(total, None) == Decimal("1.508")
