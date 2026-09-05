"""冲压零件核价计算 / 批量操作范围校验。"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.exceptions.base import BusinessException
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostScopeDTO
from app.services.costing.stamping_part_cost.calc.constants import SCOPE_REQUIRED_MESSAGE


@dataclass(frozen=True, slots=True)
class PartCostCalcScope:
    year: int
    month: int
    location: str
    vehicle_model: str
    version: str | None
    stamping_supplier: str | None


def _optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def require_scope(dto: StampingPartCostScopeDTO) -> PartCostCalcScope:
    """批量删除：车型必填；工厂可选（按查询收窄）。"""
    location = (dto.location or "").strip()
    vehicle_model = (dto.vehicle_model or "").strip()
    if not dto.year or not dto.month or not location or not vehicle_model:
        raise BusinessException(SCOPE_REQUIRED_MESSAGE)
    return PartCostCalcScope(
        year=dto.year,
        month=dto.month,
        location=location,
        vehicle_model=vehicle_model,
        version=_optional_text(dto.version),
        stamping_supplier=_optional_text(dto.stamping_supplier),
    )


def require_calc_scope(dto: StampingPartCostScopeDTO) -> PartCostCalcScope:
    """计算与批量审/反审：按整车覆盖各厂，忽略工厂筛。"""
    return replace(require_scope(dto), stamping_supplier=None)


require_audit_scope = require_calc_scope
