"""操作日志请求上下文：挂在 request.state，避免 BaseHTTPMiddleware 丢 ContextVar。"""

from __future__ import annotations

from typing import TypedDict

from starlette.requests import Request

from app.schemas.vo.user_vo import UserVO

_STATE_KEY = "operation_log_user"
_PERM_KEY = "operation_log_permission_code"
_SCOPE_KEY = "operation_log_audit_scope"
_UPLOAD_FILENAMES_KEY = "operation_log_upload_filenames"


class OperationAuditScope(TypedDict, total=False):
    """落到对象列的业务口径。"""

    location: str
    part_number: str
    year: str
    month: str
    question: str


def set_request_user(request: Request, user: UserVO | None) -> None:
    """在鉴权成功后写入，供操作日志中间件读取。"""
    setattr(request.state, _STATE_KEY, user)


def get_request_user(request: Request) -> UserVO | None:
    return getattr(request.state, _STATE_KEY, None)


def set_request_permission(request: Request, code: str | None) -> None:
    """在 require_perm 通过后写入，供操作日志对照 catalog。"""
    setattr(request.state, _PERM_KEY, code)


def get_request_permission(request: Request) -> str | None:
    value = getattr(request.state, _PERM_KEY, None)
    if value is None:
        return None
    return str(value)


def set_request_audit_scope(request: Request, scope: OperationAuditScope) -> None:
    """业务路由写入口径（基地/零件号/年/月），供操作日志摘要使用。"""
    setattr(request.state, _SCOPE_KEY, scope)


def get_request_audit_scope(request: Request) -> OperationAuditScope | None:
    value = getattr(request.state, _SCOPE_KEY, None)
    if not isinstance(value, dict):
        return None
    scope: OperationAuditScope = {}
    location = value.get("location")
    if isinstance(location, str) and location.strip():
        scope["location"] = location.strip()
    part_number = value.get("part_number")
    if isinstance(part_number, str) and part_number.strip():
        scope["part_number"] = part_number.strip()
    year = value.get("year")
    if isinstance(year, str) and year.strip():
        scope["year"] = year.strip()
    month = value.get("month")
    if isinstance(month, str) and month.strip():
        scope["month"] = month.strip()
    question = value.get("question")
    if isinstance(question, str) and question.strip():
        scope["question"] = question.strip()
    return scope or None


def set_request_upload_filenames(request: Request, filenames: list[str]) -> None:
    """上传接口解析出的原始文件名，供操作日志摘要/对象列使用。"""
    cleaned = [item.strip() for item in filenames if item.strip()]
    setattr(request.state, _UPLOAD_FILENAMES_KEY, cleaned)


def get_request_upload_filenames(request: Request) -> list[str] | None:
    value = getattr(request.state, _UPLOAD_FILENAMES_KEY, None)
    if not isinstance(value, list):
        return None
    names = [str(item).strip() for item in value if str(item).strip()]
    return names or None
