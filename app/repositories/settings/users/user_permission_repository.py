"""用户权限 Repository"""

from sqlalchemy.orm import Session

from app.models.settings import UserPermission


class UserPermissionRepository:
    """仅数据库访问"""

    def list_codes(self, db: Session, user_id: int) -> list[str]:
        rows = (
            db.query(UserPermission.permission_code)
            .filter(UserPermission.user_id == user_id)
            .order_by(UserPermission.permission_code.asc())
            .all()
        )
        return [r[0] for r in rows]

    def replace_codes(self, db: Session, user_id: int, codes: list[str]) -> list[str]:
        """覆盖写入用户权限，返回最终 code 列表。调用方负责 commit。"""
        db.query(UserPermission).filter(UserPermission.user_id == user_id).delete(
            synchronize_session=False
        )
        unique_codes = sorted(set(codes))
        for code in unique_codes:
            db.add(UserPermission(user_id=user_id, permission_code=code))
        db.flush()
        return unique_codes

    def ensure_codes(self, db: Session, user_id: int, codes: list[str]) -> list[str]:
        """补齐缺失 code（不删已有），返回合并后列表。调用方负责 commit。"""
        existing = set(self.list_codes(db, user_id))
        missing = [c for c in codes if c not in existing]
        for code in missing:
            db.add(UserPermission(user_id=user_id, permission_code=code))
        if missing:
            db.flush()
        return sorted(existing | set(codes))
