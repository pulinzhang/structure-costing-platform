"""操作日志中间件：写操作 + 文件导出自动落库。"""

from __future__ import annotations

import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.common.operation_log.context import (
    get_request_audit_scope,
    get_request_permission,
    get_request_upload_filenames,
    get_request_user,
)
from app.common.operation_log.rules import should_record
from app.services.settings.logs.operation_log_service import OperationLogService

logger = logging.getLogger("middleware.operation_log")
_service = OperationLogService()


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


class OperationLogMiddleware(BaseHTTPMiddleware):
    """请求结束后按规则写入 operation_logs。"""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        response = await call_next(request)

        try:
            method = request.method
            path = request.url.path
            path_only = path.split("?", 1)[0]
            # 登录失败不记（账号密码错误等）；成功才落入操作日志
            if path_only.rstrip("/") == "/api/auth/login" and response.status_code >= 400:
                return response
            if should_record(method, path):
                user = get_request_user(request)
                raw_params = getattr(request, "path_params", {}) or {}
                path_params = {str(key): str(value) for key, value in raw_params.items()}
                _service.record_from_request(
                    user=user,
                    method=method,
                    path=path,
                    query_string=request.url.query or "",
                    status_code=response.status_code,
                    client_ip=_client_ip(request),
                    permission_code=get_request_permission(request),
                    path_params=path_params or None,
                    audit_scope=get_request_audit_scope(request),
                    upload_filenames=get_request_upload_filenames(request),
                )
        except Exception:
            logger.exception("操作日志中间件异常（已忽略）")

        return response
