"""用户 Repository - 仅数据库访问"""

from typing import Any

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.models.user import User


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
    ):
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
    ) -> dict[str, int]:
        """按与列表相同的筛选条件汇总：启用 / 管理员。"""
        q = self._build_list_query(
            db,
            keyword=keyword,
            username=username,
            real_name=real_name,
            is_active=is_active,
        )
        row = q.with_entities(
            func.sum(case((User.is_active.is_(True), 1), else_=0)).label(
                "active_count"
            ),
            func.sum(case((User.is_admin.is_(True), 1), else_=0)).label(
                "admin_count"
            ),
        ).one()
        return {
            "active_count": int(row.active_count or 0),
            "admin_count": int(row.admin_count or 0),
        }

    def list_all(self, db: Session) -> list[User]:
        return db.query(User).order_by(User.id.asc()).all()

    def create(self, db: Session, data: dict[str, Any]) -> User:
        user = User(**data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update(self, db: Session, user_id: int, data: dict[str, Any]) -> User | None:
        user = self.get_by_id(db, user_id)
        if not user:
            return None
        for key, value in data.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user

    def delete(self, db: Session, user_id: int) -> bool:
        user = self.get_by_id(db, user_id)
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True

    def count(self, db: Session) -> int:
        return db.query(User).count()
