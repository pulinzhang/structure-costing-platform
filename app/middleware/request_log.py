"""访问日志：方法、路径、状态码、耗时。"""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logging_config import get_logger, log_request, log_response

logger = get_logger("middleware.request")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        log_request(logger, request.method, request.url.path)
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        log_response(logger, request.method, request.url.path, response.status_code, duration_ms)
        return response
