"""冲压零件核价计算领域模型。"""

from __future__ import annotations

from collections.abc import Callable

from app.exceptions.base import BusinessException

ProgressCallback = Callable[[int, str], None]


class DuplicateScopeCalcError(BusinessException):
    """同一计算范围已有进行中的任务。"""

    def __init__(self, message: str = "同一计算范围已有进行中的任务。") -> None:
        super().__init__(message=message, code=409)
