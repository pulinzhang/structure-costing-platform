"""路由层权限依赖：统一拦截。

用法：
    from app.common.permissions.codes import Perm

    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW))
    current_user: UserVO = Depends(require_any_perm(Perm.STAMPING_PARTS_VIEW, Perm.STEEL_PRICE_CALC_VIEW))
    current_user: UserVO = Depends(require_admin_user)
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request

from app.common.operation_log.context import set_request_permission
from app.common.permissions.catalog import is_valid_code
from app.common.permissions.checks import (
    has_permission,
    require_admin,
    require_any_permission,
    require_permission,
)
from app.deps.auth import get_current_user
from app.schemas.vo.user_vo import UserVO


def require_perm(code: str) -> Callable[..., UserVO]:
    """返回校验指定权限码的依赖（含登录校验）。"""
    if not is_valid_code(code):
        raise ValueError(f"未知权限码: {code}（请同步 catalog.json 与 codes.Perm）")

    def _dependency(
        request: Request,
        current_user: UserVO = Depends(get_current_user),
    ) -> UserVO:
        require_permission(current_user, code)
        set_request_permission(request, code)
        return current_user

    _dependency.__name__ = f"require_perm_{code.replace(':', '_')}"
    return _dependency


def require_any_perm(*codes: str) -> Callable[..., UserVO]:
    """拥有任一权限码即可。"""
    if not codes:
        raise ValueError("require_any_perm 至少需要一个权限码")
    for code in codes:
        if not is_valid_code(code):
            raise ValueError(f"未知权限码: {code}（请同步 catalog.json 与 codes.Perm）")

    def _dependency(
        request: Request,
        current_user: UserVO = Depends(get_current_user),
    ) -> UserVO:
        require_any_permission(current_user, list(codes))
        set_request_permission(request, _pick_matched_permission(current_user, codes))
        return current_user

    _dependency.__name__ = "require_any_perm_" + "_".join(c.replace(":", "_") for c in codes)
    return _dependency


def require_admin_user(
    current_user: UserVO = Depends(get_current_user),
) -> UserVO:
    """仅管理员可访问。"""
    require_admin(current_user)
    return current_user


def _pick_matched_permission(user: UserVO, codes: tuple[str, ...]) -> str:
    """any 权限取用户实际命中的码；管理员记路由声明的第一项。"""
    if not codes:
        return ""
    if getattr(user, "is_admin", False):
        return codes[0]
    for code in codes:
        if has_permission(user, code):
            return code
    return codes[0]
