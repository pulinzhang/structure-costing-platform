"""冲压零件核价计算范围：车型必填。"""

import pytest
from pydantic import ValidationError

from app.exceptions.base import BusinessException
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.services.costing.stamping_part_cost.calc.constants import (
    CALC_SCOPE_REQUIRED_MESSAGE,
)
from app.services.costing.stamping_part_cost.calc.scope import require_calc_scope


def test_calc_dto_requires_vehicle_model() -> None:
    with pytest.raises(ValidationError):
        StampingPartCostCalcDTO(
            year=2026,
            month=1,
            location="青岛",
            stamping_supplier="一工厂",
        )


def test_require_calc_scope_returns_vehicle_model() -> None:
    dto = StampingPartCostCalcDTO(
        year=2026,
        month=1,
        location="青岛",
        stamping_supplier="一工厂",
        vehicle_model="T2AA",
    )
    location, supplier, vehicle_model = require_calc_scope(dto)
    assert location == "青岛"
    assert supplier == "一工厂"
    assert vehicle_model == "T2AA"


def test_require_calc_scope_rejects_blank_vehicle_model() -> None:
    dto = StampingPartCostCalcDTO.model_construct(
        year=2026,
        month=1,
        location="青岛",
        stamping_supplier="一工厂",
        vehicle_model="  ",
    )
    with pytest.raises(BusinessException, match=CALC_SCOPE_REQUIRED_MESSAGE):
        require_calc_scope(dto)
