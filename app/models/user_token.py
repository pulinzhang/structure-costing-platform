"""登录 Token 表 — 落在辅助库（auxiliary.db），与主业务库隔离。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String

from app.database import AuxiliaryBase
from app.models.audit_mixin import AuditUserMixin


class UserToken(AuditUserMixin, AuxiliaryBase):
    """用户登录 Token：3 小时无活动自动失效"""

    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(64), unique=True, nullable=False, index=True, comment="登录令牌")

    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    username = Column(String(50), nullable=False, comment="登录账号")
    real_name = Column(String(50), nullable=True, comment="姓名")
    email = Column(String(100), nullable=True, comment="邮箱")
    department = Column(String(50), nullable=True, comment="部门")
    avatar = Column(String(255), nullable=True, comment="头像")

    last_active_at = Column(DateTime, default=datetime.now, nullable=False, comment="最后活动时间")

    __table_args__ = (
        Index("ix_user_tokens_user_active", "user_id", "last_active_at"),
    )
