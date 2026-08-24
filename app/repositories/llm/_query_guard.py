"""Repository 查询守卫：慢查询日志（C.5.1）。不做 SQL 超时熔断。"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from app.utils.logging_config import get_logger

logger = get_logger("repository.llm.query_guard")

T = TypeVar("T")


def run_guarded_query(
    *,
    sql_summary: str,
    trace_id: str | None,
    query_fn: Callable[[], T],
) -> T:
    started = time.perf_counter()
    result = query_fn()
    elapsed = time.perf_counter() - started
    trace_label = trace_id or "-"
    if elapsed > 1.0:
        logger.warning(
            "慢查询 trace_id=%s elapsed=%.3fs sql=%s",
            trace_label,
            elapsed,
            sql_summary,
        )
    return result
