"""冲压零件核价 / 加工费：计算按车型覆盖各厂；批量可按工厂收窄查询。"""

import pytest
from pydantic import ValidationError

from app.exceptions.base import BusinessException
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostCalcDTO,
    StampingPartCostDeleteDTO,
)
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeCalcDTO
from app.services.costing.stamping_part_cost.calc.constants import SCOPE_REQUIRED_MESSAGE
from app.services.costing.stamping_part_cost.calc.scope import (
    require_audit_scope,
    require_calc_scope,
    require_scope,
)
from app.services.stamping.process_fee.rules.scope import (
    SCOPE_REQUIRED_MESSAGE as PROCESS_FEE_SCOPE_REQUIRED,
)
from app.services.stamping.process_fee.rules.scope import (
    require_audit_scope as require_process_fee_audit_scope,
)
from app.services.stamping.process_fee.rules.scope import (
    require_calc_scope as require_process_fee_calc_scope,
)
from app.services.stamping.process_fee.rules.scope import (
    require_scope as require_process_fee_scope,
)


def test_calc_dto_requires_vehicle_model() -> None:
    with pytest.raises(ValidationError):
        StampingPartCostCalcDTO(
            year=2026,
            month=1,
            location="青岛",
            stamping_supplier="一工厂",
        )


def test_calc_scope_ignores_supplier() -> None:
    dto = StampingPartCostCalcDTO(
        year=2026,
        month=1,
        location="青岛",
        vehicle_model="T2AA",
        stamping_supplier="一工厂",
    )
    scope = require_calc_scope(dto)
    assert scope.vehicle_model == "T2AA"
    assert scope.stamping_supplier is None
    assert require_audit_scope is require_calc_scope


def test_require_calc_scope_rejects_blank_vehicle_model() -> None:
    dto = StampingPartCostCalcDTO.model_construct(
        year=2026,
        month=1,
        location="青岛",
        vehicle_model="  ",
    )
    with pytest.raises(BusinessException, match=SCOPE_REQUIRED_MESSAGE):
        require_calc_scope(dto)


def test_audit_scope_ignores_supplier() -> None:
    dto = StampingPartCostDeleteDTO(
        year=2026,
        month=1,
        location="青岛",
        vehicle_model="T2AA",
        stamping_supplier="一工厂",
    )
    scope = require_audit_scope(dto)
    assert scope.stamping_supplier is None
    assert scope.vehicle_model == "T2AA"


def test_batch_scope_keeps_optional_supplier() -> None:
    dto = StampingPartCostDeleteDTO(
        year=2026,
        month=1,
        location="青岛",
        vehicle_model="T2AA",
        stamping_supplier="一工厂",
    )
    scope = require_scope(dto)
    assert scope.stamping_supplier == "一工厂"


def test_batch_scope_rejects_missing_vehicle() -> None:
    with pytest.raises(ValidationError):
        StampingPartCostDeleteDTO(
            year=2026,
            month=1,
            location="青岛",
            stamping_supplier="一工厂",
        )
    dto = StampingPartCostDeleteDTO.model_construct(
        year=2026,
        month=1,
        location="青岛",
        vehicle_model="  ",
    )
    with pytest.raises(BusinessException, match=SCOPE_REQUIRED_MESSAGE):
        require_scope(dto)


def test_process_fee_requires_vehicle_not_mill_only() -> None:
    with pytest.raises(ValidationError):
        StampingProcessFeeCalcDTO(year=2026, location="青岛")
    with pytest.raises(ValidationError):
        StampingProcessFeeCalcDTO(year=2026, location="青岛", stamping_supplier="一工厂")
    scope = require_process_fee_calc_scope(
        StampingProcessFeeCalcDTO(
            year=2026,
            location="青岛",
            vehicle_model="T13J",
            stamping_supplier="一工厂",
        )
    )
    assert scope.vehicle_model == "T13J"
    assert scope.stamping_supplier is None


def test_process_fee_batch_keeps_optional_supplier() -> None:
    scope = require_process_fee_scope(
        StampingProcessFeeCalcDTO(
            year=2026,
            location="青岛",
            vehicle_model="T13J",
            stamping_supplier="一工厂",
        )
    )
    assert scope.stamping_supplier == "一工厂"
    audit = require_process_fee_audit_scope(
        StampingProcessFeeCalcDTO(
            year=2026,
            location="青岛",
            vehicle_model="T13J",
            stamping_supplier="一工厂",
        )
    )
    assert audit.stamping_supplier is None
    with pytest.raises(BusinessException, match=PROCESS_FEE_SCOPE_REQUIRED):
        require_process_fee_scope(
            StampingProcessFeeCalcDTO.model_construct(
                year=2026,
                location="青岛",
                vehicle_model="  ",
            )
        )
