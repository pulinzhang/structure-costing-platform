"""用户 Repository - 仅数据库访问"""

from typing import TypedDict

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Query, Session

from app.models.settings import User
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.user_dto import UserInsertPayload, UserPatchPayload


class UserFilterSummary(TypedDict):
    """用户列表筛选汇总。"""

    active_count: int
    admin_count: int


class UserListFilters(TypedDict):
    """用户分页接口附带的筛选体。"""

    summary: UserFilterSummary


class UserRepository:
    """用户数据访问"""

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, db: Session, username: str) -> User | None:
        return db.query(User).filter(User.username == username).first()

    def _build_list_query(
        self,
        db: Session,
        keyword: str | None = None,
        username: str | None = None,
        real_name: str | None = None,
        is_active: bool | None = None,
    ) -> Query[User]:
        q = db.query(User)
        if keyword:
            pattern = f"%{keyword}%"
            q = q.filter(
                or_(
                    User.username.like(pattern),
                    User.real_name.like(pattern),
                )
            )
        else:
            if username:
                q = q.filter(User.username.like(f"%{username}%"))
            if real_name:
                q = q.filter(User.real_name.like(f"%{real_name}%"))
        if is_active is not None:
            q = q.filter(User.is_active == is_active)
        return q

    def paginate(
        self,
        db: Session,
        keyword: str | None = None,
        username: str | None = None,
        real_name: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        q = self._build_list_query(
            db,
            keyword=keyword,
            username=username,
            real_name=real_name,
            is_active=is_active,
        )
        total = q.count()
        rows = q.order_by(User.id.desc()).offset(skip).limit(limit).all()
        return rows, total

    def summarize_by_filters(
        self,
        db: Session,
        keyword: str | None = None,
        username: str | None = None,
        real_name: str | None = None,
        is_active: bool | None = None,
    ) -> UserFilterSummary:
        """按与列表相同的筛选条件汇总：启用 / 管理员。"""
        q = self._build_list_query(
            db,
            keyword=keyword,
            username=username,
            real_name=real_name,
            is_active=is_active,
        )
        row = q.with_entities(
            func.sum(case((User.is_active.is_(True), 1), else_=0)).label("active_count"),
            func.sum(case((User.is_admin.is_(True), 1), else_=0)).label("admin_count"),
        ).one()
        return {
            "active_count": int(row.active_count or 0),
            "admin_count": int(row.admin_count or 0),
        }

    def list_all(self, db: Session) -> list[User]:
        return db.query(User).order_by(User.id.asc()).all()

    def create(self, db: Session, data: UserInsertPayload) -> User:
        user = model_from_payload(User, data)
        db.add(user)
        db.flush()
        db.refresh(user)
        return user

    def update(self, db: Session, user_id: int, data: UserPatchPayload) -> User | None:
        user = self.get_by_id(db, user_id)
        if not user:
            return None
        apply_payload_fields(user, data, skip=frozenset({"id", "created_by", "created_at"}))
        db.flush()
        db.refresh(user)
        return user

    def delete(self, db: Session, user_id: int) -> bool:
        user = self.get_by_id(db, user_id)
        if not user:
            return False
        db.delete(user)
        db.flush()
        return True

    def count(self, db: Session) -> int:
        return db.query(User).count()
