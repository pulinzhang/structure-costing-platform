"""操作日志失败原因：context、handler、422 摘要、Service 截断。"""

from __future__ import annotations

import asyncio
from collections.abc import Generator

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.common.operation_log.context import (
    get_request_error_message,
    set_request_error_message,
)
from app.common.operation_log.error_message import (
    ERROR_MESSAGE_MAX_LENGTH,
    GENERIC_PUBLIC_ERROR,
    HTTP_EXCEPTION_FALLBACK,
    clip_error_message,
    http_exception_error_message,
    parse_validation_errors,
)
from app.exceptions.base import BusinessException
from app.exceptions.handlers import (
    business_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.models.settings.operation_log import OperationLog
from app.services.settings.logs.service import OperationLogService


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/stamping/parts",
            "raw_path": b"/api/stamping/parts",
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
    )


def test_context_set_get_error_message() -> None:
    request = _request()
    assert get_request_error_message(request) is None
    set_request_error_message(request, "  权限不足: op:demo  ")
    assert get_request_error_message(request) == "权限不足: op:demo"


def test_http_exception_non_str_detail_falls_back() -> None:
    assert http_exception_error_message([{"msg": "nope"}]) == HTTP_EXCEPTION_FALLBACK
    assert http_exception_error_message({"msg": "nope"}) == HTTP_EXCEPTION_FALLBACK
    assert http_exception_error_message("  未登录  ") == "未登录"


def test_parse_validation_includes_field_not_input() -> None:
    secret = "hunter2-secret-value"
    items, audit = parse_validation_errors(
        [
            {
                "loc": ("body", "year"),
                "msg": "Field required",
                "type": "missing",
                "input": {"password": secret, "year": None},
                "ctx": {"given": secret},
            }
        ]
    )
    assert items == [{"field": "year", "error": "Field required"}]
    assert "year（Field required）" in audit
    assert audit.startswith("请求参数校验失败：")
    assert secret not in audit


def test_parse_validation_empty_loc() -> None:
    items, audit = parse_validation_errors(
        [{"loc": ("body",), "msg": "JSON decode error", "input": {"raw": "not-json"}}]
    )
    assert items == [{"field": "", "error": "JSON decode error"}]
    assert audit == "请求参数校验失败（JSON decode error）"
    assert "：" not in audit
    assert "not-json" not in audit


def test_clip_error_message_truncates() -> None:
    long_text = "字" * 400
    clipped = clip_error_message(long_text)
    assert len(clipped) == ERROR_MESSAGE_MAX_LENGTH
    assert clipped.endswith("…")


def test_handlers_write_request_state() -> None:
    request = _request()
    asyncio.run(business_exception_handler(request, BusinessException("期别已锁定")))
    assert get_request_error_message(request) == "期别已锁定"

    request = _request()
    asyncio.run(
        http_exception_handler(
            request,
            HTTPException(status_code=401, detail="未登录或登录已过期"),
        )
    )
    assert get_request_error_message(request) == "未登录或登录已过期"

    request = _request()
    asyncio.run(
        http_exception_handler(
            request,
            HTTPException(status_code=400, detail=[{"msg": "bad"}]),
        )
    )
    assert get_request_error_message(request) == HTTP_EXCEPTION_FALLBACK

    request = _request()
    asyncio.run(generic_exception_handler(request, RuntimeError("traceback-secret")))
    assert get_request_error_message(request) == GENERIC_PUBLIC_ERROR
    assert "traceback-secret" not in (get_request_error_message(request) or "")


def test_validation_handler_keeps_json_contract() -> None:
    request = _request()
    exc = RequestValidationError(
        [
            {
                "type": "missing",
                "loc": ("body", "month"),
                "msg": "Field required",
                "input": {"password": "should-not-appear"},
            }
        ]
    )
    response = asyncio.run(validation_exception_handler(request, exc))
    assert response.status_code == 422
    payload = response.body
    assert b"should-not-appear" not in payload
    audit = get_request_error_message(request)
    assert audit is not None
    assert "month（Field required）" in audit
    assert "should-not-appear" not in audit


@pytest.fixture
def logs_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    OperationLog.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(
        "app.services.settings.logs.service.DatabaseConfig.get_session_factory",
        lambda: factory,
    )
    monkeypatch.setattr(
        "app.services.settings.logs.service._schedule_ip_lookup",
        lambda _log_id, _client_ip: None,
    )
    try:
        yield factory
    finally:
        engine.dispose()


def test_service_clips_error_on_failure(
    logs_session_factory: sessionmaker[Session],
) -> None:
    OperationLogService().record_from_request(
        user=None,
        method="POST",
        path="/api/stamping/parts",
        query_string="",
        status_code=400,
        client_ip=None,
        error_message="错" * 400,
    )
    db = logs_session_factory()
    try:
        row = db.query(OperationLog).one()
        assert row.success is False
        assert row.error_message is not None
        assert len(row.error_message) == ERROR_MESSAGE_MAX_LENGTH
        assert row.error_message.endswith("…")
    finally:
        db.close()


def test_service_skips_error_on_success(
    logs_session_factory: sessionmaker[Session],
) -> None:
    OperationLogService().record_from_request(
        user=None,
        method="POST",
        path="/api/stamping/parts",
        query_string="",
        status_code=200,
        client_ip=None,
        error_message="不该写入",
    )
    db = logs_session_factory()
    try:
        row = db.query(OperationLog).one()
        assert row.success is True
        assert row.error_message is None
    finally:
        db.close()
