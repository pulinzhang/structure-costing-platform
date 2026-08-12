"""用户模型"""

from sqlalchemy import Boolean, Column, Integer, String

from app.database import Base
from app.models.audit_mixin import AuditUserMixin


class User(AuditUserMixin, Base):
    """系统用户表"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="登录账号")
    password_hash = Column(String(32), nullable=False, comment="密码摘要 MD5(salt+password)")

    real_name = Column(String(50), nullable=True, comment="姓名")
    email = Column(String(100), nullable=True, comment="邮箱")
    phone = Column(String(20), nullable=True, comment="电话")
    department = Column(String(50), nullable=True, comment="部门")
    avatar = Column(
        String(255),
        nullable=True,
        default=None,
        comment="头像相对路径，如 /uploads/avatars/xxx.png；空则前端显示首字母",
    )

    is_active = Column(Boolean, default=True, nullable=False, comment="启用状态")
    is_admin = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="超级管理员：拥有全部权限，可授权",
    )
