"""API 文档入口只接受配置里的账号密码，页面资源走本地。"""

from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.factory import build_fastapi
from app.config import settings
from app.middleware.docs_auth import DocsAuthMiddleware


def _client() -> TestClient:
    app = FastAPI()

    @app.get("/login")
    def login_page() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(DocsAuthMiddleware)
    return TestClient(app)


def test_docs_requires_configured_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SWAGGER_USERNAME", "docs_user")
    monkeypatch.setattr(settings, "SWAGGER_PASSWORD", "docs_pass")
    client = _client()

    denied = client.get("/docs")
    assert denied.status_code == 401
    assert denied.headers["www-authenticate"].startswith("Basic")

    wrong = client.get("/docs", auth=("docs_user", "wrong"))
    assert wrong.status_code == 401

    allowed = client.get("/docs", auth=("docs_user", "docs_pass"))
    assert allowed.status_code == 200
    assert "swagger" in allowed.text.lower()

    blocked_schema = client.get("/openapi.json")
    assert blocked_schema.status_code == 401
    schema = client.get("/openapi.json", auth=("docs_user", "docs_pass"))
    assert schema.status_code == 200

    blocked_redoc = client.get("/redoc")
    assert blocked_redoc.status_code == 401
    redoc = client.get("/redoc", auth=("docs_user", "docs_pass"))
    assert redoc.status_code == 200


def test_blank_docs_credentials_reject_any_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SWAGGER_USERNAME", "")
    monkeypatch.setattr(settings, "SWAGGER_PASSWORD", "")
    response = _client().get("/docs", auth=("anyone", "anything"))
    assert response.status_code == 401


def test_docs_html_uses_local_assets() -> None:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield

    client = TestClient(build_fastapi(lifespan=lifespan))
    response = client.get("/docs")
    assert response.status_code == 200
    assert "/static/js/vendor/scalar/api-reference.js" in response.text
    assert "/static/css/fonts.css" in response.text
    assert "Scalar.createApiReference" in response.text
    assert '"withDefaultFonts": false' in response.text
    assert '"locale": "zh-CN"' in response.text
    assert '"disabled": true' in response.text
    assert "cdn.jsdelivr.net" not in response.text
    assert "fonts.googleapis.com" not in response.text
    assert "fonts.scalar.com" not in response.text
    assert "swagger-ui" not in response.text
    assert '"forceDarkModeState": "light"' in response.text
    assert '"hideDarkModeToggle": true' in response.text
    script_at = response.text.find("/static/js/vendor/scalar/api-reference.js")
    menu_css_at = response.text.find("font-sidebar:not(:hover)")
    assert "font-sidebar-active:not(.bg-sidebar-b-active):not(:hover)" in response.text
    assert '"showSidebar"' not in response.text
    assert '"defaultOpenFirstTag": false' in response.text
    assert "#description/introduction" not in response.text
    assert "syncSidebarSections" in response.text
    assert script_at != -1
    assert menu_css_at > script_at
    assert "#666666" in response.text
    assert "#010101" in response.text
    assert "#b70826" in response.text

    redirected = client.get("/redoc", follow_redirects=False)
    assert redirected.status_code == 307
    assert redirected.headers["location"] == "/docs"


def test_other_routes_skip_docs_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SWAGGER_USERNAME", "docs_user")
    monkeypatch.setattr(settings, "SWAGGER_PASSWORD", "docs_pass")
    response = _client().get("/login")
    assert response.status_code == 200
