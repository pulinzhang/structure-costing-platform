"""Token Repository"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.models.settings import UserToken
from app.repositories.persist import model_from_payload, query_update
from app.schemas.dto.user_dto import UserTokenCreate, UserTokenSnapshot

# 无活动超时：3 小时
TOKEN_IDLE_HOURS = 3


class UserTokenRepository:
    """登录 Token 数据访问"""

    def get_by_token(self, db: Session, token: str) -> UserToken | None:
        return db.query(UserToken).filter(UserToken.token == token).first()

    def create(self, db: Session, data: UserTokenCreate) -> UserToken:
        row = model_from_payload(UserToken, data)
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def touch(self, db: Session, token: str, active_at: datetime | None = None) -> UserToken | None:
        row = self.get_by_token(db, token)
        if not row:
            return None
        current_time = active_at or now()
        row.last_active_at = current_time
        row.updated_at = current_time
        username = str(row.username or "")
        real_name = str(row.real_name) if row.real_name else None
        row.updated_by = (real_name or username).strip() or username
        db.flush()
        db.refresh(row)
        return row

    def delete_by_token(self, db: Session, token: str) -> bool:
        row = self.get_by_token(db, token)
        if not row:
            return False
        db.delete(row)
        db.flush()
        return True

    def delete_by_user_id(self, db: Session, user_id: int) -> int:
        count = (
            db.query(UserToken)
            .filter(UserToken.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.flush()
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
        db.flush()
        return count

    def sync_user_snapshot(
        self, db: Session, user_id: int, snapshot: UserTokenSnapshot
    ) -> int:
        """资料变更后，同步该用户所有 token 上的展示字段"""
        values: dict[str, str | datetime | None] = {
            "username": snapshot["username"],
            "real_name": snapshot["real_name"],
            "email": snapshot["email"],
            "department": snapshot["department"],
            "avatar": snapshot["avatar"],
            "updated_at": now(),
        }
        count = query_update(
            db.query(UserToken).filter(UserToken.user_id == user_id),
            values,
        )
        db.flush()
        return count

    def delete_expired(self, db: Session, idle_hours: int = TOKEN_IDLE_HOURS) -> int:
        """删除超过 idle_hours 无活动的 token"""
        deadline = now() - timedelta(hours=idle_hours)
        count = (
            db.query(UserToken)
            .filter(UserToken.last_active_at < deadline)
            .delete(synchronize_session=False)
        )
        db.flush()
        return count
