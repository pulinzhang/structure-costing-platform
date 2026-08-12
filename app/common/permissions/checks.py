"""权限校验辅助（Service / Router 共用）。"""

from __future__ import annotations

from app.exceptions.base import PermissionException
from app.schemas.vo.user_vo import UserVO


def has_permission(user: UserVO, code: str) -> bool:
    """判断用户是否拥有权限码。is_admin 或 permissions 含 * 视为全量。"""
    if not user:
        return False
    if getattr(user, "is_admin", False):
        return True
    permissions = getattr(user, "permissions", None) or []
    if "*" in permissions:
        return True
    return code in permissions


def require_admin(user: UserVO, message: str = "仅管理员可执行此操作") -> None:
    if not user or not getattr(user, "is_admin", False):
        raise PermissionException(message)


def require_permission(
    user: UserVO,
    code: str,
    message: str | None = None,
) -> None:
    """无权限则抛 PermissionException（HTTP 403）。is_admin 放行。"""
    if has_permission(user, code):
        return
    raise PermissionException(message or f"权限不足: {code}")


def require_any_permission(
    user: UserVO,
    codes: list[str],
    message: str | None = None,
) -> None:
    """拥有 codes 中任一权限即通过。"""
    if not codes:
        raise PermissionException(message or "权限不足")
    if any(has_permission(user, code) for code in codes):
        return
    raise PermissionException(message or f"权限不足: {' / '.join(codes)}")
