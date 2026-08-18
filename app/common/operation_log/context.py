"""操作日志请求上下文：挂在 request.state，避免 BaseHTTPMiddleware 丢 ContextVar。"""

from __future__ import annotations

from starlette.requests import Request

from app.schemas.vo.user_vo import UserVO

_STATE_KEY = "operation_log_user"


def set_request_user(request: Request, user: UserVO | None) -> None:
    """在鉴权成功后写入，供操作日志中间件读取。"""
    setattr(request.state, _STATE_KEY, user)


def get_request_user(request: Request) -> UserVO | None:
    return getattr(request.state, _STATE_KEY, None)
