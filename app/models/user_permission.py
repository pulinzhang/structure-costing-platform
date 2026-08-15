"""用户权限关联表"""

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserPermission(Base):
    """用户已授权的权限码（扁平存储）"""

    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_code", name="uq_user_permission"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户 ID",
    )
    permission_code: Mapped[str] = mapped_column(String(100), nullable=False, comment="权限码")
