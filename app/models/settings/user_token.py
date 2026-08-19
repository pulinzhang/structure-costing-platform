"""登录 Token 表 — 落在辅助库（auxiliary.db），与主业务库隔离。"""

from datetime import datetime
from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.common.timezone import now
from app.database import AuxiliaryBase
from app.models.common.audit_mixin import AuditUserMixin

class UserToken(AuditUserMixin, AuxiliaryBase):
    """用户登录 Token：3 小时无活动自动失效"""

    __tablename__ = "user_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True, comment="登录令牌")

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="登录账号")
    real_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="姓名")
    email: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="邮箱")
    department: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="部门")
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="头像")

    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False, comment="最后活动时间（东八区墙钟）")

    __table_args__ = (
        Index("ix_user_tokens_user_active", "user_id", "last_active_at"),
    )
