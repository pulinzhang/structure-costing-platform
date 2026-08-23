"""Repository 查询守卫：超时熔断 + 慢查询日志（C.5.1）。"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from app.config import settings
from app.utils.logging_config import get_logger

logger = get_logger("repository.llm.query_guard")

T = TypeVar("T")


class LlmQueryTimeoutError(TimeoutError):
    """SQL 执行超过熔断阈值。"""

    def __init__(
        self,
        *,
        elapsed_seconds: float,
        sql_summary: str,
        timeout_seconds: int,
    ) -> None:
        self.elapsed_seconds = elapsed_seconds
        self.sql_summary = sql_summary
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"查询超时（{elapsed_seconds:.2f}s > {timeout_seconds}s）: {sql_summary}"
        )


def run_guarded_query(
    *,
    sql_summary: str,
    trace_id: str | None,
    query_fn: Callable[[], T],
    timeout_seconds: int = settings.LLM_SQL_TIMEOUT_SECONDS,
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
    if elapsed > timeout_seconds:
        raise LlmQueryTimeoutError(
            elapsed_seconds=elapsed,
            sql_summary=sql_summary,
            timeout_seconds=timeout_seconds,
        )
    return result
