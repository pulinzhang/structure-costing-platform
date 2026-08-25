"""异步任务 worker 横切类型与结果映射（不含 Session / 线程）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

# 与 async_task_service.STATUS_* 同值，避免循环 import
_STATUS_COMPLETED = "completed"
_STATUS_FAILED = "failed"

ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True)
class WorkerTaskOutcome:
    """切片 work() 的任务终态；runner 原样写入辅助库。"""

    status: str
    message: str
    result: object | None = None
    progress: int = 100


WorkerWork = Callable[[Session, ProgressCallback], WorkerTaskOutcome]
CrashCallback = Callable[[Session, BaseException], None]
CrashMessageFn = Callable[[BaseException], str]
CrashResultFn = Callable[[BaseException], object | None]


def calc_status_label(status: str) -> str:
    """计算类 result.status → 中文标签。"""
    return {"success": "成功", "partial": "部分成功"}.get(status, status)


def outcome_from_calc_status(
    status: str,
    *,
    failed_message: str,
    completed_message: str,
    result: object | None,
) -> WorkerTaskOutcome:
    """result.status == failed → 任务 FAILED，否则 COMPLETED。"""
    if status == "failed":
        return WorkerTaskOutcome(
            status=_STATUS_FAILED,
            progress=100,
            message=failed_message,
            result=result,
        )
    return WorkerTaskOutcome(
        status=_STATUS_COMPLETED,
        progress=100,
        message=completed_message,
        result=result,
    )
