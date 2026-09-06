"""加工费计算内部模型。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from app.exceptions.base import BusinessException

ProgressCallback = Callable[[int, str], None]


@dataclass
class ProcessTonnageResolveResult:
    """工序吨位解析结果（成功时）。"""

    tonnage: int | None
    source: str
    inherited_from_part_id: int | None = None
    inherited_from_part_number: str | None = None
    inherited_from_process_seq: str | None = None
    inherited_from_process_code: str | None = None


@dataclass
class TonnageRateInfo:
    """冲次单价快照。"""

    price_per_stroke: Decimal
    tonnage_price_id: int | None = None


class DuplicateScopeCalcError(BusinessException):
    """同一计算范围已有进行中的任务。"""

    def __init__(self, message: str = "同一计算范围已有进行中的任务。") -> None:
        super().__init__(message=message, code=409)
