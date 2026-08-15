"""冲压零件核价计算领域模型。"""

from __future__ import annotations

from typing import Callable

ProgressCallback = Callable[[int, str], None]


class DuplicateScopeCalcError(Exception):
    """同一计算范围已有进行中的任务。"""
