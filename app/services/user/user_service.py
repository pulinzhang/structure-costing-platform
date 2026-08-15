"""用户 Service - 业务逻辑"""

import hashlib
import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.config import settings
from app.common.audit import (
    SYSTEM_USER,
    audit_create,
    audit_update,
)
from app.common.permissions.checks import require_permission
from app.repositories.user.user_repository import UserRepository
from app.schemas.dto.user_dto import (
    UserCreateDTO,
    UserPasswordUpdateDTO,
    UserQueryDTO,
    UserSelfPasswordUpdateDTO,
    UserSelfUpdateDTO,
    UserUpdateDTO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.user.permission_service import PermissionService

from app.utils.avatar_storage import delete_avatar_file, save_user_avatar

logger = logging.getLogger("service.user")

DEFAULT_AVATAR: str | None = None


def hash_password_md5(password: str) -> str:
    """MD5(salt + password)，输出 32 位 hex。"""
    raw = f"{settings.PASSWORD_SALT}{password}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class UserService:
    """用户业务逻辑"""

    def __init__(self) -> None:
        self.repository = UserRepository()
        self.permission_service = PermissionService()

    def _to_vo(self, db: Session, user) -> UserVO:
        vo = UserVO.model_validate(user)
        vo.permissions = self.permission_service.resolve_permissions_for_user(db, user)
        return vo

    def list_users(self, db: Session) -> list[UserVO]:
        users = self.repository.list_all(db)
        return [self._to_vo(db, u) for u in users]

    def paginate(
        self, db: Session, query: UserQueryDTO
    ) -> tuple[list[UserVO], int, dict]:
        skip = (query.page - 1) * query.size
        filter_kwargs = dict(
            keyword=query.keyword,
            username=query.username,
            real_name=query.real_name,
            is_active=query.is_active,
        )
        rows, total = self.repository.paginate(
            db,
            **filter_kwargs,
            skip=skip,
            limit=query.size,
        )
        filters = {
            "summary": self.repository.summarize_by_filters(db, **filter_kwargs),
        }
        return [self._to_vo(db, u) for u in rows], total, filters

    def get_by_id(self, db: Session, user_id: int) -> UserVO | None:
        user = self.repository.get_by_id(db, user_id)
        if not user:
            return None
        return self._to_vo(db, user)

    def create(
        self,
        db: Session,
        dto: UserCreateDTO,
        current_user: UserVO,
    ) -> UserVO:
        require_permission(current_user, Perm.SETTINGS_USERS_CREATE)
        if self.repository.get_by_username(db, dto.username):
            raise ValueError(f"账号已存在: {dto.username}")

        data: dict[str, Any] = {
            "username": dto.username.strip(),
            "password_hash": hash_password_md5(dto.password),
            "real_name": dto.real_name,
            "email": dto.email,
            "phone": dto.phone,
            "department": dto.department,
            "avatar": dto.avatar or DEFAULT_AVATAR,
            "is_active": dto.is_active,
            "is_admin": False,
            **audit_create(current_user),
        }
        try:
            user = self.repository.create(db, data)
            self.permission_service.assign_defaults(db, user.id, commit=True)
            return self._to_vo(db, user)
        except IntegrityError as exc:
            db.rollback()
            logger.warning("创建用户失败（唯一约束）: %s", exc)
            raise ValueError(f"账号已存在: {dto.username}") from exc

    def update(
        self,
        db: Session,
        user_id: int,
        dto: UserUpdateDTO,
        current_user: UserVO,
    ) -> UserVO | None:
        require_permission(current_user, Perm.SETTINGS_USERS_UPDATE)
        data = dto.model_dump(exclude_unset=True)
        if not data:
            return self.get_by_id(db, user_id)
        data.update(audit_update(current_user))
        user = self.repository.update(db, user_id, data)
        if not user:
            return None
        return self._to_vo(db, user)

    def update_own_profile(
        self,
        db: Session,
        current_user: UserVO,
        dto: UserSelfUpdateDTO,
    ) -> UserVO:
        """当前用户更新自己的资料（不含启用状态）"""
        require_permission(current_user, Perm.SETTINGS_PROFILE_UPDATE)
        data = dto.model_dump(exclude_unset=True)
        data.update(audit_update(current_user))
        user = self.repository.update(db, current_user.id, data)
        if not user:
            raise ValueError("用户不存在")
        return self._to_vo(db, user)

    def update_own_avatar(
        self,
        db: Session,
        current_user: UserVO,
        *,
        file_content: bytes,
        filename: str,
    ) -> UserVO:
        """当前用户上传头像，写入 uploads/avatars/ 并更新 avatar 字段"""
        require_permission(current_user, Perm.SETTINGS_PROFILE_UPDATE)
        existing = self.repository.get_by_id(db, current_user.id)
        if not existing:
            raise ValueError("用户不存在")

        avatar_url = save_user_avatar(
            user_id=current_user.id,
            file_content=file_content,
            filename=filename,
        )
        # 新文件落盘成功后再删旧文件，避免上传失败导致丢头像
        old_avatar = existing.avatar
        updated = self.repository.update(
            db,
            current_user.id,
            {
                "avatar": avatar_url,
                **audit_update(current_user),
            },
        )
        if not updated:
            delete_avatar_file(avatar_url)
            raise ValueError("用户不存在")
        delete_avatar_file(old_avatar)
        return self._to_vo(db, updated)

    def update_password(
        self,
        db: Session,
        user_id: int,
        dto: UserPasswordUpdateDTO,
        current_user: UserVO,
    ) -> UserVO | None:
        require_permission(current_user, Perm.SETTINGS_USERS_PASSWORD)
        user = self.repository.update(
            db,
            user_id,
            {
                "password_hash": hash_password_md5(dto.password),
                **audit_update(current_user),
            },
        )
        if not user:
            return None
        return self._to_vo(db, user)

    def change_own_password(
        self,
        db: Session,
        current_user: UserVO,
        dto: UserSelfPasswordUpdateDTO,
    ) -> UserVO:
        """当前用户改密：先校验旧密码，再写入新密码。"""
        require_permission(current_user, Perm.SETTINGS_PROFILE_PASSWORD)
        user = self.repository.get_by_id(db, current_user.id)
        if not user:
            raise ValueError("用户不存在")
        if user.password_hash != hash_password_md5(dto.old_password):
            raise ValueError("当前密码不正确")
        if dto.old_password == dto.password:
            raise ValueError("新密码不能与当前密码相同")

        updated = self.repository.update(
            db,
            current_user.id,
            {
                "password_hash": hash_password_md5(dto.password),
                **audit_update(current_user),
            },
        )
        if not updated:
            raise ValueError("用户不存在")
        return self._to_vo(db, updated)

    def delete(self, db: Session, user_id: int, current_user: UserVO) -> bool:
        require_permission(current_user, Perm.SETTINGS_USERS_DELETE)
        target = self.repository.get_by_id(db, user_id)
        if not target:
            return False
        if target.is_admin:
            admin_count = sum(1 for u in self.repository.list_all(db) if u.is_admin)
            if admin_count <= 1:
                raise ValueError("不能删除最后一个管理员")
        return self.repository.delete(db, user_id)

    def ensure_default_admin(self, db: Session) -> None:
        """首次启动时若无用户，创建默认管理员 admin / admin123"""
        if self.repository.count(db) > 0:
            self.permission_service.ensure_bootstrap(db)
            return
        data: dict[str, Any] = {
            "username": "admin",
            "password_hash": hash_password_md5("admin123"),
            "real_name": "系统管理员",
            "department": "系统",
            "avatar": DEFAULT_AVATAR,
            "is_active": True,
            "is_admin": True,
            **audit_create(SYSTEM_USER),
        }
        self.repository.create(db, data)
        logger.info("已创建默认管理员账号: admin / admin123")
        self.permission_service.ensure_bootstrap(db)
