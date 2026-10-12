"""用户 Service - 业务逻辑"""

import hashlib
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import (
    SYSTEM_USER,
    audit_create,
    audit_update,
)
from app.common.permissions.checks import require_admin, require_permission
from app.common.permissions.codes import Perm
from app.config import settings
from app.exceptions.base import BusinessException, NotFoundException
from app.models.settings import User
from app.repositories.settings.users.user_repository import (
    UserListFilters,
    UserRepository,
)
from app.schemas.dto.user_dto import (
    UserCreateDTO,
    UserInsertPayload,
    UserPasswordUpdateDTO,
    UserPatchPayload,
    UserQueryDTO,
    UserSelfPasswordUpdateDTO,
    UserSelfUpdateDTO,
    UserUpdateDTO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.settings.users.permission import PermissionService
from app.utils.avatar_storage import delete_avatar_file, save_user_avatar

logger = logging.getLogger("service.user")

DEFAULT_AVATAR: str | None = None


def _user_patch_from_dto(
    dto: UserUpdateDTO | UserSelfUpdateDTO,
    *,
    updated_by: str,
) -> UserPatchPayload:
    patch: UserPatchPayload = {"updated_by": updated_by}
    fields_set = dto.model_fields_set
    if "real_name" in fields_set:
        patch["real_name"] = dto.real_name
    if "email" in fields_set:
        patch["email"] = dto.email
    if "phone" in fields_set:
        patch["phone"] = dto.phone
    if "department" in fields_set:
        patch["department"] = dto.department
    if isinstance(dto, UserUpdateDTO):
        if "avatar" in fields_set:
            patch["avatar"] = dto.avatar
        if "is_active" in fields_set and dto.is_active is not None:
            patch["is_active"] = dto.is_active
        if "is_admin" in fields_set and dto.is_admin is not None:
            patch["is_admin"] = dto.is_admin
    return patch


def hash_password_md5(password: str) -> str:
    """MD5(salt + password)，输出 32 位 hex。"""
    raw = f"{settings.PASSWORD_SALT}{password}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class UserService:
    """用户业务逻辑"""

    def __init__(self) -> None:
        self.repository = UserRepository()
        self.permission_service = PermissionService()

    def _to_vo(self, db: Session, user: User) -> UserVO:
        vo = UserVO.model_validate(user)
        vo.permissions = self.permission_service.resolve_permissions_for_user(db, user)
        return vo

    def list_users(self, db: Session) -> list[UserVO]:
        users = self.repository.list_all(db)
        return [self._to_vo(db, u) for u in users]

    def paginate(
        self, db: Session, query: UserQueryDTO
    ) -> tuple[list[UserVO], int, UserListFilters]:
        skip = (query.page - 1) * query.size
        rows, total = self.repository.paginate(
            db,
            keyword=query.keyword,
            username=query.username,
            real_name=query.real_name,
            is_active=query.is_active,
            skip=skip,
            limit=query.size,
        )
        filters: UserListFilters = {
            "summary": self.repository.summarize_by_filters(
                db,
                keyword=query.keyword,
                username=query.username,
                real_name=query.real_name,
                is_active=query.is_active,
            ),
        }
        return [self._to_vo(db, u) for u in rows], total, filters

    def get_by_id(self, db: Session, user_id: int) -> UserVO:
        user = self.repository.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("用户不存在")
        return self._to_vo(db, user)

    def _admin_flag_changed(
        self,
        db: Session,
        existing: User,
        dto: UserUpdateDTO,
        current_user: UserVO,
    ) -> bool:
        """管理员标记有变化时返回 True。仅管理员可改，且不能取消最后一个。"""
        if "is_admin" not in dto.model_fields_set or dto.is_admin is None:
            return False
        if dto.is_admin == existing.is_admin:
            return False
        require_admin(current_user, "仅管理员可设置管理员")
        if existing.is_admin and not dto.is_admin:
            admin_count = sum(1 for user in self.repository.list_all(db) if user.is_admin)
            if admin_count <= 1:
                raise BusinessException("不能取消最后一个管理员")
        return True

    def create(
        self,
        db: Session,
        dto: UserCreateDTO,
        current_user: UserVO,
    ) -> UserVO:
        require_permission(current_user, Perm.SETTINGS_USERS_CREATE)
        if dto.is_admin:
            require_admin(current_user, "仅管理员可设置管理员")
        if self.repository.get_by_username(db, dto.username):
            raise BusinessException(f"账号已存在: {dto.username}")

        audit = audit_create(current_user)
        payload = UserInsertPayload(
            username=dto.username.strip(),
            password_hash=hash_password_md5(dto.password),
            real_name=dto.real_name,
            email=dto.email,
            phone=dto.phone,
            department=dto.department,
            avatar=dto.avatar or DEFAULT_AVATAR,
            is_active=dto.is_active,
            is_admin=dto.is_admin,
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
        )
        try:
            user = self.repository.create(db, payload)
            # 同一事务：用户 + 默认权限一起提交
            self.permission_service.assign_defaults(db, user.id, commit=False)
            db.commit()
            db.refresh(user)
            return self._to_vo(db, user)
        except IntegrityError as exc:
            db.rollback()
            logger.warning("创建用户失败（唯一约束）: %s", exc)
            raise BusinessException(f"账号已存在: {dto.username}") from exc

    def update(
        self,
        db: Session,
        user_id: int,
        dto: UserUpdateDTO,
        current_user: UserVO,
        *,
        token_db: Session,
    ) -> UserVO:
        require_permission(current_user, Perm.SETTINGS_USERS_UPDATE)
        if not dto.model_fields_set:
            return self.get_by_id(db, user_id)
        existing = self.repository.get_by_id(db, user_id)
        if not existing:
            raise NotFoundException("用户不存在")
        was_admin = existing.is_admin
        admin_changed = self._admin_flag_changed(db, existing, dto, current_user)
        user = self.repository.update(
            db,
            user_id,
            _user_patch_from_dto(dto, updated_by=audit_update(current_user)["updated_by"]),
        )
        if not user:
            raise NotFoundException("用户不存在")
        if (
            admin_changed
            and was_admin
            and dto.is_admin is False
            and not self.permission_service.perm_repo.list_codes(db, user_id)
        ):
            self.permission_service.assign_defaults(db, user_id, commit=False)
        db.commit()
        db.refresh(user)
        if admin_changed or ("is_active" in dto.model_fields_set and dto.is_active is False):
            from app.services.settings.users.auth import AuthService

            AuthService().revoke_all_sessions(token_db, user.id)
        return self._to_vo(db, user)

    def update_own_profile(
        self,
        db: Session,
        current_user: UserVO,
        dto: UserSelfUpdateDTO,
    ) -> UserVO:
        """当前用户更新自己的资料（不含启用状态）"""
        require_permission(current_user, Perm.SETTINGS_PROFILE_UPDATE)
        user = self.repository.update(
            db,
            current_user.id,
            _user_patch_from_dto(dto, updated_by=audit_update(current_user)["updated_by"]),
        )
        if not user:
            raise NotFoundException("用户不存在")
        db.commit()
        db.refresh(user)
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
            raise NotFoundException("用户不存在")

        try:
            avatar_url = save_user_avatar(
                user_id=current_user.id,
                file_content=file_content,
                filename=filename,
            )
        except ValueError as exc:
            raise BusinessException(str(exc)) from exc
        # 新文件落盘成功后再删旧文件，避免上传失败导致丢头像
        old_avatar = existing.avatar
        updated = self.repository.update(
            db,
            current_user.id,
            {
                "avatar": avatar_url,
                "updated_by": audit_update(current_user)["updated_by"],
            },
        )
        if not updated:
            delete_avatar_file(avatar_url)
            raise NotFoundException("用户不存在")
        db.commit()
        db.refresh(updated)
        delete_avatar_file(old_avatar)
        return self._to_vo(db, updated)

    def update_password(
        self,
        db: Session,
        user_id: int,
        dto: UserPasswordUpdateDTO,
        current_user: UserVO,
    ) -> UserVO:
        require_permission(current_user, Perm.SETTINGS_USERS_PASSWORD)
        user = self.repository.update(
            db,
            user_id,
            {
                "password_hash": hash_password_md5(dto.password),
                "updated_by": audit_update(current_user)["updated_by"],
            },
        )
        if not user:
            raise NotFoundException("用户不存在")
        db.commit()
        db.refresh(user)
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
            raise NotFoundException("用户不存在")
        if user.password_hash != hash_password_md5(dto.old_password):
            raise BusinessException("当前密码不正确")
        if dto.old_password == dto.password:
            raise BusinessException("新密码不能与当前密码相同")

        updated = self.repository.update(
            db,
            current_user.id,
            {
                "password_hash": hash_password_md5(dto.password),
                "updated_by": audit_update(current_user)["updated_by"],
            },
        )
        if not updated:
            raise NotFoundException("用户不存在")
        db.commit()
        db.refresh(updated)
        return self._to_vo(db, updated)

    def delete(self, db: Session, user_id: int, current_user: UserVO) -> None:
        require_permission(current_user, Perm.SETTINGS_USERS_DELETE)
        target = self.repository.get_by_id(db, user_id)
        if not target:
            raise NotFoundException("用户不存在")
        if target.is_admin:
            admin_count = sum(1 for u in self.repository.list_all(db) if u.is_admin)
            if admin_count <= 1:
                raise BusinessException("不能删除最后一个管理员")
        ok = self.repository.delete(db, user_id)
        if not ok:
            raise NotFoundException("用户不存在")
        db.commit()

    def ensure_default_admin(self, db: Session) -> None:
        """首次启动时若无用户，创建默认管理员 admin / admin123"""
        if self.repository.count(db) > 0:
            self.permission_service.ensure_bootstrap(db)
            return
        audit = audit_create(SYSTEM_USER)
        payload = UserInsertPayload(
            username="admin",
            password_hash=hash_password_md5("admin123"),
            real_name="系统管理员",
            department="系统",
            avatar=DEFAULT_AVATAR,
            is_active=True,
            is_admin=True,
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
        )
        self.repository.create(db, payload)
        logger.info("已创建默认管理员账号: admin / admin123")
        # ensure_bootstrap 内统一 commit（含刚创建的 admin）
        self.permission_service.ensure_bootstrap(db)
