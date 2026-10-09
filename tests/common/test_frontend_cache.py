"""入口页每次核对；带 ?v= 的脚本和样式长期缓存。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.frontend import register_frontend
from app.middleware.frontend_cache import frontend_cache_control

_NO_CACHE = "no-cache, must-revalidate"
_VERSIONED = "public, max-age=31536000, immutable"


def test_entry_pages_revalidate() -> None:
    assert frontend_cache_control("/", None) == _NO_CACHE
    assert frontend_cache_control("/app", None) == _NO_CACHE
    assert frontend_cache_control("/login", "884") == _NO_CACHE


def test_versioned_assets_are_immutable() -> None:
    assert frontend_cache_control("/static/js/app.js", "884") == _VERSIONED
    assert frontend_cache_control("/static/css/tailwind.css", "35") == _VERSIONED


def test_unversioned_assets_revalidate() -> None:
    assert frontend_cache_control("/static/js/vendor/marked.min.js", None) == _NO_CACHE
    assert frontend_cache_control("/static/js/vendor/marked.min.js", "") == _NO_CACHE


def test_api_is_untouched() -> None:
    assert frontend_cache_control("/api/dashboard/stats", None) is None


def test_root_serves_dashboard_shell() -> None:
    app = FastAPI()
    register_frontend(app)
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.history == []
    assert 'href="#/dashboard"' in response.text
    assert "登录 - 结构件自动核价平台" not in response.text
