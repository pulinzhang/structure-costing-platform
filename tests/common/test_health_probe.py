"""容器健康检查：轻量地址，并且不进访问日志。"""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.frontend import HEALTH_PATH, register_frontend
from app.middleware.request_log import RequestLogMiddleware
from app.utils.logging_config import HealthProbeAccessFilter, attach_health_probe_access_filter


def test_health_probe_returns_ok_without_request_log(caplog: pytest.LogCaptureFixture) -> None:
    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)
    register_frontend(app)
    with caplog.at_level(logging.INFO):
        response = TestClient(app).get(HEALTH_PATH)
    assert response.status_code == 200
    assert response.text == "ok"
    assert "请求:" not in caplog.text
    assert "响应:" not in caplog.text


def test_health_probe_skipped_in_uvicorn_access_log() -> None:
    probe = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, "%s", (), None)
    probe.args = ("127.0.0.1:1", "GET", HEALTH_PATH, "1.1", 200)
    page = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, "%s", (), None)
    page.args = ("127.0.0.1:1", "GET", "/login", "1.1", 200)
    access_filter = HealthProbeAccessFilter()
    assert access_filter.filter(probe) is False
    assert access_filter.filter(page) is True


def test_attach_health_probe_access_filter_once() -> None:
    attach_health_probe_access_filter()
    attach_health_probe_access_filter()
    access_logger = logging.getLogger("uvicorn.access")
    matched = [item for item in access_logger.filters if isinstance(item, HealthProbeAccessFilter)]
    assert len(matched) == 1
