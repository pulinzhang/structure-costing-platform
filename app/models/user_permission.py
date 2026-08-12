"""用户权限关联表"""

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class UserPermission(Base):
    """用户已授权的权限码（扁平存储）"""

    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_code", name="uq_user_permission"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户 ID",
    )
    permission_code = Column(String(100), nullable=False, comment="权限码")
