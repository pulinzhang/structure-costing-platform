"""用户 Service - 业务逻辑"""

import hashlib
import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.common.audit import (
    SYSTEM_USER,
    audit_create,
    audit_update,
)
from app.repositories.user.user_repository import UserRepository
from app.schemas.dto.user_dto import (
    UserCreateDTO,
    UserPasswordUpdateDTO,
    UserQueryDTO,
    UserUpdateDTO,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.user")

DEFAULT_AVATAR = "/static/avatars/default.png"


def hash_password_md5(password: str) -> str:
    """MD5(salt + password)，输出 32 位 hex。"""
    raw = f"{settings.PASSWORD_SALT}{password}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class UserService:
    """用户业务逻辑"""

    def __init__(self) -> None:
        self.repository = UserRepository()

    def _to_vo(self, user) -> UserVO:
        return UserVO.model_validate(user)

    def list_users(self, db: Session) -> list[UserVO]:
        users = self.repository.list_all(db)
        return [self._to_vo(u) for u in users]

    def paginate(self, db: Session, query: UserQueryDTO) -> tuple[list[UserVO], int]:
        skip = (query.page - 1) * query.size
        rows, total = self.repository.paginate(
            db,
            username=query.username,
            real_name=query.real_name,
            is_active=query.is_active,
            skip=skip,
            limit=query.size,
        )
        return [self._to_vo(u) for u in rows], total

    def get_by_id(self, db: Session, user_id: int) -> UserVO | None:
        user = self.repository.get_by_id(db, user_id)
        if not user:
            return None
        return self._to_vo(user)

    def create(
        self,
        db: Session,
        dto: UserCreateDTO,
        current_user: UserVO,
    ) -> UserVO:
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
            **audit_create(current_user),
        }
        try:
            user = self.repository.create(db, data)
            return self._to_vo(user)
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
        data = dto.model_dump(exclude_unset=True)
        if not data:
            return self.get_by_id(db, user_id)
        data.update(audit_update(current_user))
        user = self.repository.update(db, user_id, data)
        if not user:
            return None
        return self._to_vo(user)

    def update_password(
        self,
        db: Session,
        user_id: int,
        dto: UserPasswordUpdateDTO,
        current_user: UserVO,
    ) -> UserVO | None:
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
        return self._to_vo(user)

    def delete(self, db: Session, user_id: int) -> bool:
        return self.repository.delete(db, user_id)

    def ensure_default_admin(self, db: Session) -> None:
        """首次启动时若无用户，创建默认管理员 admin / admin123"""
        if self.repository.count(db) > 0:
            return
        self.create(
            db,
            UserCreateDTO(
                username="admin",
                password="admin123",
                real_name="系统管理员",
                department="系统",
                is_active=True,
            ),
            current_user=SYSTEM_USER,
        )
        logger.info("已创建默认管理员账号: admin / admin123")
