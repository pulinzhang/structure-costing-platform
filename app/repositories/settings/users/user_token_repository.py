"""Token Repository"""

from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.timezone import now
from app.models.user_token import UserToken

# 无活动超时：3 小时
TOKEN_IDLE_HOURS = 3


class UserTokenRepository:
    """登录 Token 数据访问"""

    def get_by_token(self, db: Session, token: str) -> UserToken | None:
        return db.query(UserToken).filter(UserToken.token == token).first()

    def create(self, db: Session, data: dict[str, Any]) -> UserToken:
        row = UserToken(**data)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def touch(self, db: Session, token: str, active_at: datetime | None = None) -> UserToken | None:
        row = self.get_by_token(db, token)
        if not row:
            return None
        current_time = active_at or now()
        row.last_active_at = current_time
        row.updated_at = current_time
        row.updated_by = display_name(row)
        db.commit()
        db.refresh(row)
        return row

    def delete_by_token(self, db: Session, token: str) -> bool:
        row = self.get_by_token(db, token)
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True

    def delete_by_user_id(self, db: Session, user_id: int) -> int:
        count = (
            db.query(UserToken)
            .filter(UserToken.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return count

    def delete_other_tokens(self, db: Session, user_id: int, keep_token: str) -> int:
        """注销该用户除 keep_token 以外的全部会话"""
        count = (
            db.query(UserToken)
            .filter(
                UserToken.user_id == user_id,
                UserToken.token != keep_token,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return count

    def sync_user_snapshot(self, db: Session, user_id: int, snapshot: dict[str, Any]) -> int:
        """资料变更后，同步该用户所有 token 上的展示字段"""
        allowed = {
            "username",
            "real_name",
            "email",
            "department",
            "avatar",
        }
        payload = {key: value for key, value in snapshot.items() if key in allowed}
        if not payload:
            return 0
        payload["updated_at"] = now()
        count = (
            db.query(UserToken)
            .filter(UserToken.user_id == user_id)
            .update(cast(Any, payload), synchronize_session=False)
        )
        db.commit()
        return count

    def delete_expired(self, db: Session, idle_hours: int = TOKEN_IDLE_HOURS) -> int:
        """删除超过 idle_hours 无活动的 token"""
        deadline = now() - timedelta(hours=idle_hours)
        count = (
            db.query(UserToken)
            .filter(UserToken.last_active_at < deadline)
            .delete(synchronize_session=False)
        )
        db.commit()
        return count
