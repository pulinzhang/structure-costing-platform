"""冲压零件核价计算范围校验。"""

from __future__ import annotations

from app.exceptions.base import BusinessException
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostScopeDTO
from app.services.costing.stamping_part_cost.calc.constants import SCOPE_REQUIRED_MESSAGE


def require_scope(dto: StampingPartCostScopeDTO) -> tuple[str, str]:
    location = (dto.location or "").strip()
    supplier = (dto.stamping_supplier or "").strip()
    if not dto.year or not dto.month or not location or not supplier:
        raise BusinessException(SCOPE_REQUIRED_MESSAGE)
    return location, supplier
