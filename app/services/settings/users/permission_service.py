"""权限业务：目录树、用户授权读写。"""

from __future__ import annotations

from typing import Any


from sqlalchemy.orm import Session

from app.common.permissions.catalog import (
    get_all_codes,
    get_defaults,
    get_mandatory,
    get_tree,
    is_valid_code,
)
from app.common.permissions.checks import require_admin
from app.exceptions.base import NotFoundException, ValidationException
from app.repositories.settings.users.user_permission_repository import UserPermissionRepository
from app.repositories.settings.users.user_repository import UserRepository
from app.schemas.vo.user_vo import UserVO


class PermissionService:
    """权限目录与用户授权"""

    def __init__(self) -> None:
        self.user_repo = UserRepository()
        self.perm_repo = UserPermissionRepository()

    def get_permission_tree(self, current_user: UserVO) -> list[dict[str, Any]]:
        require_admin(current_user)
        return get_tree()

    def get_user_permission_codes(
        self,
        db: Session,
        user_id: int,
        current_user: UserVO,
    ) -> list[str]:
        require_admin(current_user)
        user = self.user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("用户不存在")
        if user.is_admin:
            return sorted(get_all_codes())
        return self.perm_repo.list_codes(db, user_id)

    def set_user_permissions(
        self,
        db: Session,
        user_id: int,
        codes: list[str],
        current_user: UserVO,
    ) -> list[str]:
        """覆盖保存用户权限；强制合并 mandatory；过滤非法 code。"""
        require_admin(current_user)
        user = self.user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("用户不存在")
        if user.is_admin:
            raise ValidationException("管理员拥有全部权限，无需单独授权")

        valid = [c for c in codes if is_valid_code(c)]
        final_codes = sorted(set(valid) | set(get_mandatory()))
        result = self.perm_repo.replace_codes(db, user_id, final_codes)
        db.commit()
        return result

    def assign_defaults(self, db: Session, user_id: int, *, commit: bool = True) -> list[str]:
        """新建用户写入默认权限（含强制项）。"""
        codes = get_defaults()
        result = self.perm_repo.replace_codes(db, user_id, codes)
        if commit:
            db.commit()
        return result

    def resolve_permissions_for_user(self, db: Session, user: Any) -> list[str]:
        """组装 UserVO.permissions：admin → ['*']，否则读表。"""
        if getattr(user, "is_admin", False):
            return ["*"]
        return self.perm_repo.list_codes(db, user.id)

    def ensure_bootstrap(self, db: Session) -> None:
        """
        启动补齐：
        - 若无任何 is_admin，将 username=admin 标为管理员
        - 非管理员：无权限记录则写 defaults；有记录则补 mandatory
        """
        users = self.user_repo.list_all(db)
        admin_count = sum(1 for u in users if u.is_admin)
        if admin_count == 0:
            for u in users:
                if u.username == "admin":
                    u.is_admin = True
                    break

        for u in users:
            if u.is_admin:
                continue
            existing = self.perm_repo.list_codes(db, u.id)
            if not existing:
                self.perm_repo.replace_codes(db, u.id, get_defaults())
            else:
                self.perm_repo.ensure_codes(db, u.id, get_mandatory())

        db.commit()
