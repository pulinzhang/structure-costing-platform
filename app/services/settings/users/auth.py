"""登录会话 / Token 业务逻辑"""

import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.timezone import now
from app.config import settings
from app.exceptions.base import BusinessException
from app.models.settings import User, UserToken
from app.repositories.settings.login_security_repository import LoginSecurityRepository
from app.repositories.settings.users.user_repository import UserRepository
from app.repositories.settings.users.user_token_repository import UserTokenRepository
from app.schemas.dto.user_dto import UserLoginDTO, UserTokenCreate, UserTokenSnapshot
from app.schemas.vo.user_vo import AvatarUploadVO, LoginKeyVO, LoginVO, UserVO
from app.services.settings.users.login_cipher import decrypt_password, generate_login_keypair
from app.services.settings.users.permission import PermissionService
from app.services.settings.users.service import UserService, hash_password_md5

_KEY_TTL = timedelta(minutes=2)
_KEY_ISSUE_LIMIT = 30
_KEY_ISSUE_WINDOW = timedelta(minutes=1)
_LOGIN_AGAIN = "这次登录没有完成，请再点一次登录"


class AuthService:
    """登录认证与 Token 会话（users 在主库，user_tokens 在辅助库）"""

    def __init__(self) -> None:
        self.user_repo = UserRepository()
        self.token_repo = UserTokenRepository()
        self.login_security_repo = LoginSecurityRepository()
        self.permission_service = PermissionService()

    def _to_vo(self, user_db: Session, user: User) -> UserVO:
        vo = UserVO.model_validate(user)
        vo.permissions = self.permission_service.resolve_permissions_for_user(user_db, user)
        return vo

    def issue_login_key(self, token_db: Session, client_ip: str) -> LoginKeyVO:
        """签发一把两分钟有效的公钥。同一连接地址每分钟最多 30 把。"""
        current_time = now()
        peer = (client_ip or "")[:64]
        self.login_security_repo.delete_expired_challenges(token_db, current_time)
        since = current_time - _KEY_ISSUE_WINDOW
        recent = self.login_security_repo.count_recent_challenges(token_db, peer, since)
        if recent >= _KEY_ISSUE_LIMIT:
            token_db.commit()
            raise BusinessException("登录太频繁，请 1 分钟后再试")
        key_id, private_pem, public_spki = generate_login_keypair()
        self.login_security_repo.create_challenge(
            token_db,
            key_id=key_id,
            private_key_pem=private_pem,
            expires_at=current_time + _KEY_TTL,
            client_ip=peer,
        )
        token_db.commit()
        return LoginKeyVO(key_id=key_id, public_key_spki=public_spki)

    def clear_login_lock(self, token_db: Session, user_id: int) -> None:
        """删掉辅助库锁定行。管理员重置密码、删除用户时调用。"""
        self.login_security_repo.delete_lock(token_db, user_id)
        token_db.commit()

    def login(self, user_db: Session, token_db: Session, dto: UserLoginDTO) -> LoginVO:
        current_time = now()
        consumed = self.login_security_repo.consume_challenge(token_db, dto.key_id.strip())
        token_db.commit()
        if consumed is None:
            raise BusinessException(_LOGIN_AGAIN, code=400)
        private_key_pem, expires_at = consumed
        if expires_at <= current_time:
            raise BusinessException(_LOGIN_AGAIN, code=400)

        user = self.user_repo.get_by_username(user_db, dto.username.strip())
        if not user:
            raise BusinessException("账号或密码错误", code=401)
        if user.is_active is not True:
            raise BusinessException("账号已停用，无法登录", code=401)
        if self.login_security_repo.is_locked(token_db, user.id, current_time):
            minutes = self.login_security_repo.get_lock_minutes(token_db)
            raise BusinessException(f"账号已锁定，请 {minutes} 分钟后再试", code=401)

        try:
            password = decrypt_password(private_key_pem, dto.password_cipher)
        except ValueError:
            raise BusinessException(_LOGIN_AGAIN, code=400) from None
        if user.password_hash != hash_password_md5(password):
            minutes = self.login_security_repo.get_lock_minutes(token_db)
            self.login_security_repo.record_failure(
                token_db,
                user.id,
                lock_minutes=minutes,
                current_time=current_time,
            )
            token_db.commit()
            raise BusinessException("账号或密码错误", code=401)

        self.login_security_repo.delete_lock(token_db, user.id)

        # 清理过期 token，并作废该用户旧会话
        self.token_repo.delete_expired(token_db, settings.TOKEN_IDLE_MINUTES)
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

    def upload_own_avatar(
        self,
        db: Session,
        token_db: Session,
        current_user: UserVO,
        *,
        file_content: bytes,
        filename: str,
    ) -> AvatarUploadVO:
        user = UserService().update_own_avatar(
            db,
            current_user,
            file_content=file_content,
            filename=filename,
        )
        self.sync_profile_to_tokens(token_db, user)
        return AvatarUploadVO(url=user.avatar or "", message="头像上传成功")

    def touch(self, user_db: Session, token_db: Session, token: str) -> UserVO:
        """心跳探活：只校验，不顺延 last_active_at。"""
        return self.get_user_by_token(user_db, token_db, token, do_touch=False)

    def get_user_by_token(
        self,
        user_db: Session,
        token_db: Session,
        token: str,
        *,
        do_touch: bool = True,
    ) -> UserVO:
        _row, user = self._require_valid_token(user_db, token_db, token, do_touch=do_touch)
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

        deadline = row.last_active_at + timedelta(minutes=settings.TOKEN_IDLE_MINUTES)
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
