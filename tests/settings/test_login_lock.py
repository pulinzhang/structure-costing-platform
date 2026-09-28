"""登录锁定与一次性公钥。只使用内存库，不碰开发主库。"""

from __future__ import annotations

import base64
from collections.abc import Generator
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.settings.login_security import LoginChallenge, LoginLock, LoginPolicy
from app.models.settings.user import User
from app.models.settings.user_token import UserToken
from app.schemas.dto.user_dto import UserLoginDTO
from app.services.settings.users import auth as auth_module
from app.services.settings.users.auth import AuthService
from app.services.settings.users.service import hash_password_md5

_PASSWORD = "secret-pass"


def _encrypt(public_key_spki: str, password: str) -> str:
    public_key = serialization.load_der_public_key(base64.b64decode(public_key_spki))
    cipher = public_key.encrypt(
        password.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(cipher).decode("ascii")


@pytest.fixture
def login_dbs() -> Generator[tuple[Session, Session], None, None]:
    user_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    aux_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(user_engine)
    UserToken.__table__.create(aux_engine)
    LoginChallenge.__table__.create(aux_engine)
    LoginLock.__table__.create(aux_engine)
    LoginPolicy.__table__.create(aux_engine)
    user_db = sessionmaker(bind=user_engine)()
    aux_db = sessionmaker(bind=aux_engine)()
    user_db.add(
        User(
            username="admin",
            password_hash=hash_password_md5(_PASSWORD),
            is_active=True,
            is_admin=True,
        )
    )
    user_db.commit()
    try:
        yield user_db, aux_db
    finally:
        user_db.close()
        aux_db.close()
        user_engine.dispose()
        aux_engine.dispose()


def _dto(service: AuthService, aux_db: Session, username: str, password: str) -> UserLoginDTO:
    issued = service.issue_login_key(aux_db, "127.0.0.1")
    return UserLoginDTO(
        username=username,
        key_id=issued.key_id,
        password_cipher=_encrypt(issued.public_key_spki, password),
    )


def _login(service: AuthService, user_db: Session, aux_db: Session, username: str, password: str):
    return service.login(user_db, aux_db, _dto(service, aux_db, username, password))


def test_wrong_password_locks_on_third_and_blocks_correct_password(
    login_dbs: tuple[Session, Session],
) -> None:
    user_db, aux_db = login_dbs
    service = AuthService()
    for _ in range(2):
        with pytest.raises(BusinessException, match="账号或密码错误"):
            _login(service, user_db, aux_db, "admin", "nope")
    with pytest.raises(BusinessException, match="账号或密码错误"):
        _login(service, user_db, aux_db, "admin", "nope")
    row = aux_db.query(LoginLock).one()
    assert row.failed_login_count == 0
    assert row.locked_until is not None
    assert row.locked_until > now()
    with pytest.raises(BusinessException, match="账号已锁定，请 15 分钟后再试"):
        _login(service, user_db, aux_db, "admin", _PASSWORD)
    assert aux_db.query(LoginLock).one().failed_login_count == 0


def test_expired_lock_accepts_correct_password(login_dbs: tuple[Session, Session]) -> None:
    user_db, aux_db = login_dbs
    service = AuthService()
    user = user_db.query(User).one()
    aux_db.add(
        LoginLock(
            user_id=user.id,
            failed_login_count=2,
            locked_until=now() - timedelta(minutes=1),
        )
    )
    aux_db.commit()
    result = _login(service, user_db, aux_db, "admin", _PASSWORD)
    assert result.token
    assert aux_db.query(LoginLock).count() == 0


def test_unknown_inactive_and_bad_cipher_do_not_count(
    login_dbs: tuple[Session, Session],
) -> None:
    user_db, aux_db = login_dbs
    service = AuthService()
    with pytest.raises(BusinessException, match="账号或密码错误"):
        _login(service, user_db, aux_db, "missing", "nope")
    user = user_db.query(User).one()
    user.is_active = False
    user_db.commit()
    with pytest.raises(BusinessException, match="账号已停用"):
        _login(service, user_db, aux_db, "admin", "nope")
    user.is_active = True
    user_db.commit()
    issued = service.issue_login_key(aux_db, "127.0.0.1")
    garbage = UserLoginDTO(
        username="admin",
        key_id=issued.key_id,
        password_cipher=base64.b64encode(b"not-a-real-cipher").decode("ascii"),
    )
    with pytest.raises(BusinessException, match="请再点一次登录"):
        service.login(user_db, aux_db, garbage)
    assert aux_db.query(LoginLock).count() == 0


def test_key_is_single_use(login_dbs: tuple[Session, Session]) -> None:
    user_db, aux_db = login_dbs
    service = AuthService()
    dto = _dto(service, aux_db, "admin", "nope")
    with pytest.raises(BusinessException, match="账号或密码错误"):
        service.login(user_db, aux_db, dto)
    with pytest.raises(BusinessException, match="请再点一次登录"):
        service.login(user_db, aux_db, dto)
    assert aux_db.query(LoginLock).one().failed_login_count == 1


def test_lock_minutes_come_from_auxiliary_policy(login_dbs: tuple[Session, Session]) -> None:
    user_db, aux_db = login_dbs
    service = AuthService()
    service.login_security_repo.save_lock_minutes(aux_db, 45, "tester")
    aux_db.commit()
    before = now()
    for _ in range(3):
        with pytest.raises(BusinessException, match="账号或密码错误"):
            _login(service, user_db, aux_db, "admin", "nope")
    locked_until = aux_db.query(LoginLock).one().locked_until
    assert locked_until is not None
    delta = locked_until - before
    assert timedelta(minutes=44) < delta < timedelta(minutes=46)
    with pytest.raises(BusinessException, match="账号已锁定，请 45 分钟后再试"):
        _login(service, user_db, aux_db, "admin", _PASSWORD)


def test_out_of_range_policy_falls_back_to_15_minutes(
    login_dbs: tuple[Session, Session],
) -> None:
    user_db, aux_db = login_dbs
    service = AuthService()
    aux_db.add(LoginPolicy(id=1, login_lock_minutes=0))
    aux_db.commit()
    before = now()
    for _ in range(3):
        with pytest.raises(BusinessException, match="账号或密码错误"):
            _login(service, user_db, aux_db, "admin", "nope")
    locked_until = aux_db.query(LoginLock).one().locked_until
    assert locked_until is not None
    delta = locked_until - before
    assert timedelta(minutes=14) < delta < timedelta(minutes=16)


def test_clear_login_lock_removes_row(login_dbs: tuple[Session, Session]) -> None:
    user_db, aux_db = login_dbs
    service = AuthService()
    for _ in range(3):
        with pytest.raises(BusinessException, match="账号或密码错误"):
            _login(service, user_db, aux_db, "admin", "nope")
    user = user_db.query(User).one()
    service.clear_login_lock(aux_db, user.id)
    assert aux_db.query(LoginLock).count() == 0
    result = _login(service, user_db, aux_db, "admin", _PASSWORD)
    assert result.token


def test_login_key_rate_limit(
    login_dbs: tuple[Session, Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    _user_db, aux_db = login_dbs
    monkeypatch.setattr(auth_module, "_KEY_ISSUE_LIMIT", 2)
    service = AuthService()
    service.issue_login_key(aux_db, "10.0.0.8")
    service.issue_login_key(aux_db, "10.0.0.8")
    with pytest.raises(BusinessException, match="请 1 分钟后再试"):
        service.issue_login_key(aux_db, "10.0.0.8")
    issued = service.issue_login_key(aux_db, "10.0.0.9")
    assert issued.key_id
