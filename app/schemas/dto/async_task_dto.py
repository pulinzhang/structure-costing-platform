"""异步任务 DTO — Repository 写入载荷。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict


@dataclass(slots=True)
class AsyncTaskInsert:
    """异步任务新建（辅助库 AUTOCOMMIT 插入）。"""

    task_id: str
    task_type: str
    status: str
    progress: int
    message: str
    result_json: str | None
    operator_id: int | None
    operator_name: str | None
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime


class AsyncTaskPatch(TypedDict, total=False):
    """异步任务部分更新（仅出现的键会被写入）。"""

    status: str
    progress: int
    message: str
    result_json: str | None
    updated_at: datetime
    updated_by: str | None
