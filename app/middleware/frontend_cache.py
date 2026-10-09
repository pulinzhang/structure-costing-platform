"""前端 Cache-Control。

入口页和带版本号的静态文件不是同一种缓存。四年后改这里之前先看这条：

- ``/``、``/app``、``/login`` 的地址不会变，HTML 里写着 ``app.js?v=``。
  这三页必须 ``no-cache, must-revalidate``。浏览器每次核对页面，才能拿到新版本号。
  报表页同样是固定地址，头在 ``app/bootstrap/frontend.py`` 的 FileResponse 上。
- ``/static/js/``、``/static/css/`` 的请求带非空查询参数 ``v`` 时，内容变了地址就变。
  用 ``public, max-age=31536000, immutable``。第二次打开不再为每个文件回源。
- 没带 ``v`` 的脚本或样式仍 ``no-cache``。漏加版本号时不要被一年缓存卡住。
  改了这种文件，要在引用它的 HTML 或 import 上把 ``?v=`` 加一。
"""

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_NO_CACHE = "no-cache, must-revalidate"
_VERSIONED_ASSET = "public, max-age=31536000, immutable"
_ENTRY_PAGES = frozenset({"/", "/app", "/login"})


def frontend_cache_control(path: str, version: str | None) -> str | None:
    """返回应写入的 Cache-Control；不归这里管的路径返回 None。"""
    if path in _ENTRY_PAGES:
        return _NO_CACHE
    if path.startswith("/static/js/") or path.startswith("/static/css/"):
        if version:
            return _VERSIONED_ASSET
        return _NO_CACHE
    return None


class FrontendCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        header = frontend_cache_control(request.url.path, request.query_params.get("v"))
        if header is not None:
            response.headers["Cache-Control"] = header
        return response
