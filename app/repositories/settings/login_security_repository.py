"""登录锁定与一次性钥匙：只访问辅助库。"""

from datetime import datetime, timedelta

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.settings.login_security import LoginChallenge, LoginLock, LoginPolicy

_POLICY_ID = 1
_DEFAULT_LOCK_MINUTES = 15
_MIN_LOCK_MINUTES = 1
_MAX_LOCK_MINUTES = 1440
_FAIL_LIMIT = 3


def normalize_lock_minutes(minutes: int | None) -> int:
    """缺行或超出 1–1440 时按 15 分钟。"""
    if minutes is None or minutes < _MIN_LOCK_MINUTES or minutes > _MAX_LOCK_MINUTES:
        return _DEFAULT_LOCK_MINUTES
    return minutes


class LoginSecurityRepository:
    """挑战钥匙、失败计数、锁定分钟数。"""

    def delete_expired_challenges(self, db: Session, current_time: datetime) -> None:
        db.execute(delete(LoginChallenge).where(LoginChallenge.expires_at <= current_time))
        db.flush()

    def count_recent_challenges(self, db: Session, client_ip: str, since: datetime) -> int:
        return (
            db.query(LoginChallenge)
            .filter(
                LoginChallenge.client_ip == client_ip,
                LoginChallenge.created_at >= since,
            )
            .count()
        )

    def create_challenge(
        self,
        db: Session,
        *,
        key_id: str,
        private_key_pem: str,
        expires_at: datetime,
        client_ip: str,
    ) -> None:
        db.add(
            LoginChallenge(
                key_id=key_id,
                private_key_pem=private_key_pem,
                expires_at=expires_at,
                client_ip=client_ip,
            )
        )
        db.flush()

    def consume_challenge(self, db: Session, key_id: str) -> tuple[str, datetime] | None:
        """一条语句取出并删除。并发的第二次拿不到私钥。"""
        result = db.execute(
            delete(LoginChallenge)
            .where(LoginChallenge.key_id == key_id)
            .returning(LoginChallenge.private_key_pem, LoginChallenge.expires_at)
        )
        row = result.first()
        db.flush()
        if row is None:
            return None
        return str(row.private_key_pem), row.expires_at

    def is_locked(self, db: Session, user_id: int, current_time: datetime) -> bool:
        row = db.query(LoginLock).filter(LoginLock.user_id == user_id).one_or_none()
        if row is None or row.locked_until is None:
            return False
        return row.locked_until > current_time

    def delete_lock(self, db: Session, user_id: int) -> None:
        db.execute(delete(LoginLock).where(LoginLock.user_id == user_id))
        db.flush()

    def record_failure(
        self,
        db: Session,
        user_id: int,
        *,
        lock_minutes: int,
        current_time: datetime,
    ) -> None:
        """过期后从 0 计。次数在库里加 1，加到 3 则清零并写截止时间。"""
        minutes = normalize_lock_minutes(lock_minutes)
        db.execute(
            update(LoginLock)
            .where(
                LoginLock.user_id == user_id,
                LoginLock.locked_until.is_not(None),
                LoginLock.locked_until <= current_time,
            )
            .values(failed_login_count=0, locked_until=None, updated_at=current_time)
        )
        incremented = db.execute(
            update(LoginLock)
            .where(LoginLock.user_id == user_id)
            .values(
                failed_login_count=LoginLock.failed_login_count + 1,
                updated_at=current_time,
            )
            .returning(LoginLock.failed_login_count)
        ).scalar_one_or_none()
        if incremented is None:
            incremented = self._insert_first_failure(db, user_id, current_time)
        if incremented >= _FAIL_LIMIT:
            db.execute(
                update(LoginLock)
                .where(LoginLock.user_id == user_id)
                .values(
                    failed_login_count=0,
                    locked_until=current_time + timedelta(minutes=minutes),
                    updated_at=current_time,
                )
            )
        db.flush()

    def _insert_first_failure(self, db: Session, user_id: int, current_time: datetime) -> int:
        try:
            with db.begin_nested():
                db.add(
                    LoginLock(
                        user_id=user_id,
                        failed_login_count=1,
                        locked_until=None,
                        created_at=current_time,
                        updated_at=current_time,
                    )
                )
                db.flush()
            return 1
        except IntegrityError:
            incremented = db.execute(
                update(LoginLock)
                .where(LoginLock.user_id == user_id)
                .values(
                    failed_login_count=LoginLock.failed_login_count + 1,
                    updated_at=current_time,
                )
                .returning(LoginLock.failed_login_count)
            ).scalar_one()
            return int(incremented)

    def get_lock_minutes(self, db: Session) -> int:
        row = db.get(LoginPolicy, _POLICY_ID)
        if row is None:
            return _DEFAULT_LOCK_MINUTES
        return normalize_lock_minutes(row.login_lock_minutes)

    def save_lock_minutes(self, db: Session, minutes: int, updated_by: str) -> int:
        stored = normalize_lock_minutes(minutes)
        row = db.get(LoginPolicy, _POLICY_ID)
        if row is None:
            db.add(
                LoginPolicy(
                    id=_POLICY_ID,
                    login_lock_minutes=stored,
                    created_by=updated_by,
                    updated_by=updated_by,
                )
            )
        else:
            row.login_lock_minutes = stored
            row.updated_by = updated_by
        db.flush()
        return stored
