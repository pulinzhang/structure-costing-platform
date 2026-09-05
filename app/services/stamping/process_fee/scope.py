"""加工费业务范围校验。"""

from __future__ import annotations

from dataclasses import dataclass

from app.exceptions.base import BusinessException
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeScopeDTO

SCOPE_REQUIRED_MESSAGE = "须选定年度、基地。"
SCOPE_NARROW_MESSAGE = "须选定年度、基地，并选定车型或冲压工厂。"
ALL_SUPPLIERS_LOCK = "全部工厂"


@dataclass(frozen=True, slots=True)
class ProcessFeeWorkScope:
    year: int
    location: str
    vehicle_model: str | None
    version: str | None
    stamping_supplier: str | None


def _optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def require_scope(dto: StampingProcessFeeScopeDTO) -> ProcessFeeWorkScope:
    """范围校验（本切片唯一口径）：年+基地，再加车型或工厂之一。"""
    location = (dto.location or "").strip()
    vehicle_model = _optional_text(dto.vehicle_model)
    supplier = _optional_text(dto.stamping_supplier)
    if not dto.year or not location:
        raise BusinessException(SCOPE_REQUIRED_MESSAGE)
    if not vehicle_model and not supplier:
        raise BusinessException(SCOPE_NARROW_MESSAGE)
    return ProcessFeeWorkScope(
        year=dto.year,
        location=location,
        vehicle_model=vehicle_model,
        version=_optional_text(dto.version),
        stamping_supplier=supplier,
    )


def lock_supplier_key(stamping_supplier: str | None) -> str:
    """计算锁第三维：未选工厂时用「全部工厂」。"""
    return stamping_supplier or ALL_SUPPLIERS_LOCK
