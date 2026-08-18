"""加工费业务范围校验。"""

from __future__ import annotations

from app.exceptions.base import BusinessException
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeScopeDTO

SCOPE_REQUIRED_MESSAGE = "须选定年度、基地、冲压工厂。"


def require_scope(dto: StampingProcessFeeScopeDTO) -> tuple[str, str]:
    """规范化并校验范围字段（strip 后仍须齐全）。"""
    location = (dto.location or "").strip()
    supplier = (dto.stamping_supplier or "").strip()
    if not dto.year or not location or not supplier:
        raise BusinessException(SCOPE_REQUIRED_MESSAGE)
    return location, supplier
