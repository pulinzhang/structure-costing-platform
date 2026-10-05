"""入口页每次核对；带 ?v= 的脚本和样式长期缓存。"""

from app.middleware.frontend_cache import frontend_cache_control

_NO_CACHE = "no-cache, must-revalidate"
_VERSIONED = "public, max-age=31536000, immutable"


def test_entry_pages_revalidate() -> None:
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
