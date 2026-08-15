"""用户模型"""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.audit_mixin import AuditUserMixin


class User(AuditUserMixin, Base):
    """系统用户表"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False, comment="登录账号")
    password_hash: Mapped[str] = mapped_column(String(32), nullable=False, comment="密码摘要 MD5(salt+password)")

    real_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="姓名")
    email: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="邮箱")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="电话")
    department: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="部门")
    avatar: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        comment="头像相对路径，如 /uploads/avatars/xxx.png；空则前端显示首字母",
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="启用状态")
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="超级管理员：拥有全部权限，可授权",
    )
