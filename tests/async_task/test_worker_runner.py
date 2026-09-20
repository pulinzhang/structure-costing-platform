"""async_task worker runner：独立 Session、终态写入、崩溃回调。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.services.async_task.async_task_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import ProgressCallback, WorkerTaskOutcome


def _service_with_mocks(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncTaskService, MagicMock]:
    db = MagicMock()
    factory = MagicMock(return_value=db)
    monkeypatch.setattr(
        "app.services.async_task.async_task_service.DatabaseConfig.get_session_factory",
        lambda: factory,
    )
    service = AsyncTaskService()
    service.update_task_standalone = MagicMock()  # type: ignore[method-assign]
    return service, db


def test_run_in_worker_session_writes_completed_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, db = _service_with_mocks(monkeypatch)

    def work(session: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
        on_progress(50, "halfway")
        return WorkerTaskOutcome(
            status=STATUS_COMPLETED,
            message="ok",
            result={"n": 1},
        )

    service.run_in_worker_session(
        "task-1",
        start_message="start",
        work=work,
    )

    db.close.assert_called_once()
    assert any(
        call.kwargs.get("status") == STATUS_COMPLETED and call.kwargs.get("message") == "ok"
        for call in service.update_task_standalone.call_args_list
    )
    assert any(
        call.kwargs.get("progress") == 50 and call.kwargs.get("message") == "halfway"
        for call in service.update_task_standalone.call_args_list
    )


def test_run_in_worker_session_crash_calls_on_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, db = _service_with_mocks(monkeypatch)
    crash_seen: list[BaseException] = []

    def work(session: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
        raise RuntimeError("boom")

    def on_crash(session: Session, error: BaseException) -> None:
        crash_seen.append(error)

    service.run_in_worker_session(
        "task-2",
        start_message="start",
        work=work,
        on_crash=on_crash,
        crash_message=lambda error: f"计算异常: {error}",
        crash_progress=0,
        crash_result=lambda error: {"error": str(error)},
    )

    db.rollback.assert_called()
    db.close.assert_called_once()
    assert len(crash_seen) == 1
    assert isinstance(crash_seen[0], RuntimeError)
    assert any(
        call.kwargs.get("status") == STATUS_FAILED
        and call.kwargs.get("message") == "计算异常: boom"
        for call in service.update_task_standalone.call_args_list
    )
