"""加工费业务范围校验。"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.exceptions.base import BusinessException
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeScopeDTO

SCOPE_REQUIRED_MESSAGE = "须选定年度、基地、项目。"
ALL_SUPPLIERS_LOCK = "全部工厂"


@dataclass(frozen=True, slots=True)
class ProcessFeeWorkScope:
    year: int
    location: str
    vehicle_model: str
    version: str | None
    stamping_supplier: str | None


def _optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def require_scope(dto: StampingProcessFeeScopeDTO) -> ProcessFeeWorkScope:
    """批量删除：年+基地+项目必填；工厂可选（按查询收窄）。"""
    location = (dto.location or "").strip()
    vehicle_model = _optional_text(dto.vehicle_model)
    if not dto.year or not location or not vehicle_model:
        raise BusinessException(SCOPE_REQUIRED_MESSAGE)
    return ProcessFeeWorkScope(
        year=dto.year,
        location=location,
        vehicle_model=vehicle_model,
        version=_optional_text(dto.version),
        stamping_supplier=_optional_text(dto.stamping_supplier),
    )


def require_calc_scope(dto: StampingProcessFeeScopeDTO) -> ProcessFeeWorkScope:
    """计算与批量审/反审：按整车覆盖各厂，忽略工厂筛。"""
    return replace(require_scope(dto), stamping_supplier=None)


require_audit_scope = require_calc_scope
