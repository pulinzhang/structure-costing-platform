"""登录会话 / Token 业务逻辑"""

import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.models.user import User
from app.models.user_token import UserToken
from app.repositories.user.user_repository import UserRepository
from app.repositories.user.user_token_repository import TOKEN_IDLE_HOURS, UserTokenRepository
from app.schemas.dto.user_dto import UserLoginDTO
from app.schemas.vo.user_vo import LoginVO, UserVO
from app.services.user.user_service import hash_password_md5


class AuthService:
    """登录认证与 Token 会话（users 在主库，user_tokens 在辅助库）"""

    def __init__(self) -> None:
        self.user_repo = UserRepository()
        self.token_repo = UserTokenRepository()

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
        now = datetime.now()
        name = display_name(user)
        self.token_repo.create(
            token_db,
            {
                "token": token,
                "user_id": user.id,
                "username": user.username,
                "real_name": user.real_name,
                "email": user.email,
                "department": user.department,
                "avatar": user.avatar,
                "last_active_at": now,
                "created_at": now,
                "created_by": name,
                "updated_by": name,
            },
        )

        return LoginVO(
            token=token,
            user=UserVO.model_validate(user),
        )

    def logout(self, token_db: Session, token: str) -> None:
        if token:
            self.token_repo.delete_by_token(token_db, token)

    def revoke_all_sessions(self, token_db: Session, user_id: int) -> int:
        """作废该用户全部登录会话"""
        return self.token_repo.delete_by_user_id(token_db, user_id)

    def logout_other_sessions(self, token_db: Session, user_id: int, keep_token: str) -> int:
        return self.token_repo.delete_other_tokens(token_db, user_id, keep_token)

    def sync_profile_to_tokens(self, token_db: Session, user: UserVO) -> None:
        self.token_repo.sync_user_snapshot(
            token_db,
            user.id,
            {
                "username": user.username,
                "real_name": user.real_name,
                "email": user.email,
                "department": user.department,
                "avatar": user.avatar,
            },
        )

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
        return UserVO.model_validate(user)

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
        if datetime.now() > deadline:
            self.token_repo.delete_by_token(token_db, token)
            raise PermissionError("登录已超时，请重新登录")

        user = self.user_repo.get_by_id(user_db, row.user_id)
        if not user or user.is_active is not True:
            self.token_repo.delete_by_token(token_db, token)
            raise PermissionError("账号已停用")

        if do_touch:
            touched = self.token_repo.touch(token_db, token)
            return (touched or row), user
        return row, user
