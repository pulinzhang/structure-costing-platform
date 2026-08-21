"""登录会话 / Token 业务逻辑"""

import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.timezone import now
from app.models.settings import User, UserToken
from app.repositories.settings.users.user_repository import UserRepository
from app.repositories.settings.users.user_token_repository import TOKEN_IDLE_HOURS, UserTokenRepository
from app.schemas.dto.user_dto import UserLoginDTO, UserTokenCreate, UserTokenSnapshot
from app.schemas.vo.user_vo import LoginVO, UserVO
from app.services.settings.users.permission_service import PermissionService
from app.services.settings.users.user_service import hash_password_md5


class AuthService:
    """登录认证与 Token 会话（users 在主库，user_tokens 在辅助库）"""

    def __init__(self) -> None:
        self.user_repo = UserRepository()
        self.token_repo = UserTokenRepository()
        self.permission_service = PermissionService()

    def _to_vo(self, user_db: Session, user: User) -> UserVO:
        vo = UserVO.model_validate(user)
        vo.permissions = self.permission_service.resolve_permissions_for_user(user_db, user)
        return vo

    def login(self, user_db: Session, token_db: Session, dto: UserLoginDTO) -> LoginVO:
        user = self.user_repo.get_by_username(user_db, dto.username.strip())
        if not user:
            raise ValueError("账号或密码错误")
        if user.is_active is not True:
            raise ValueError("账号已停用，无法登录")
        if user.password_hash != hash_password_md5(dto.password):
            raise ValueError("账号或密码错误")

        # 清理过期 token，并作废该用户旧会话
        self.token_repo.delete_expired(token_db)
        self.token_repo.delete_by_user_id(token_db, user.id)

        token = secrets.token_hex(32)
        current_time = now()
        name = display_name(user)
        self.token_repo.create(
            token_db,
            UserTokenCreate(
                token=token,
                user_id=user.id,
                username=user.username,
                real_name=user.real_name,
                email=user.email,
                department=user.department,
                avatar=user.avatar,
                last_active_at=current_time,
                created_at=current_time,
                created_by=name,
                updated_by=name,
            ),
        )
        token_db.commit()

        return LoginVO(
            token=token,
            user=self._to_vo(user_db, user),
        )

    def logout(self, token_db: Session, token: str) -> None:
        if token:
            self.token_repo.delete_by_token(token_db, token)
            token_db.commit()

    def revoke_all_sessions(self, token_db: Session, user_id: int) -> int:
        """作废该用户全部登录会话"""
        count = self.token_repo.delete_by_user_id(token_db, user_id)
        token_db.commit()
        return count

    def logout_other_sessions(self, token_db: Session, user_id: int, keep_token: str) -> int:
        count = self.token_repo.delete_other_tokens(token_db, user_id, keep_token)
        token_db.commit()
        return count

    def sync_profile_to_tokens(self, token_db: Session, user: UserVO) -> None:
        self.token_repo.sync_user_snapshot(
            token_db,
            user.id,
            UserTokenSnapshot(
                username=user.username,
                real_name=user.real_name,
                email=user.email,
                department=user.department,
                avatar=user.avatar,
            ),
        )
        token_db.commit()

    def touch(self, user_db: Session, token_db: Session, token: str) -> UserVO:
        return self.get_user_by_token(user_db, token_db, token, do_touch=True)

    def get_user_by_token(
        self,
        user_db: Session,
        token_db: Session,
        token: str,
        *,
        do_touch: bool = True,
    ) -> UserVO:
        _row, user = self._require_valid_token(
            user_db, token_db, token, do_touch=do_touch
        )
        return self._to_vo(user_db, user)

    def _require_valid_token(
        self,
        user_db: Session,
        token_db: Session,
        token: str,
        *,
        do_touch: bool,
    ) -> tuple[UserToken, User]:
        """校验 token + 用户启用状态；只查一次 users 表。"""
        if not token:
            raise PermissionError("未登录")

        row = self.token_repo.get_by_token(token_db, token)
        if not row:
            raise PermissionError("登录已失效，请重新登录")

        deadline = row.last_active_at + timedelta(hours=TOKEN_IDLE_HOURS)
        if now() > deadline:
            self.token_repo.delete_by_token(token_db, token)
            token_db.commit()
            raise PermissionError("登录已超时，请重新登录")

        user = self.user_repo.get_by_id(user_db, row.user_id)
        if not user or user.is_active is not True:
            self.token_repo.delete_by_token(token_db, token)
            token_db.commit()
            raise PermissionError("账号已停用")

        if do_touch:
            touched = self.token_repo.touch(token_db, token)
            token_db.commit()
            return (touched or row), user
        return row, user
