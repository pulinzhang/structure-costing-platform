"""登录锁定与一次性公钥 — 落在辅助库，不改主库用户表。"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import AuxiliaryBase
from app.models.common.audit_mixin import AuditUserMixin


class LoginChallenge(AuditUserMixin, AuxiliaryBase):
    """一次性登录私钥。用后即删，过期由签发时清理。"""

    __tablename__ = "login_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="随机钥匙编号"
    )
    private_key_pem: Mapped[str] = mapped_column(
        Text, nullable=False, comment="PKCS8 私钥 PEM，接口不返回"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="过期时间（东八区墙钟）"
    )
    client_ip: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", comment="签发时的连接地址"
    )

    __table_args__ = (Index("ix_login_challenges_ip_created", "client_ip", "created_at"),)


class LoginLock(AuditUserMixin, AuxiliaryBase):
    """账号连续登录失败与锁定截止时间。没有行表示未失败、未锁定。"""

    __tablename__ = "login_locks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True, comment="用户 ID，无跨库外键"
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当前周期内的连续失败次数"
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="锁定截止时间（东八区墙钟）；空表示未锁定"
    )


class LoginPolicy(AuditUserMixin, AuxiliaryBase):
    """登录锁定分钟数。单例行 id=1。没有行时按 15 分钟。"""

    __tablename__ = "login_policies"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, comment="固定为 1"
    )
    login_lock_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15, comment="连续失败 3 次后的锁定分钟数"
    )
