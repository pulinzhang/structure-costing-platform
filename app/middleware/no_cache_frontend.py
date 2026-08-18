"""前端静态资源禁用强缓存，避免 ?v= 未变时浏览器继续使用坏脚本。"""

from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_NO_CACHE = "no-cache, must-revalidate"


class NoCacheFrontendMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        path = request.url.path
        if (
            path.startswith("/static/js/")
            or path.startswith("/static/css/")
            or path in ("/app", "/login")
        ):
            response.headers["Cache-Control"] = _NO_CACHE
        return response
