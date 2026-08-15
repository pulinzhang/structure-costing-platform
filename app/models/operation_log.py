"""操作审计日志（主库）。"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.common.timezone import now
from app.database import Base

class OperationLog(Base):
    """业务操作审计日志：写操作 + 导出。"""

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="操作人用户 ID")
    username: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True, comment="登录账号")
    operator_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="展示名")
    method: Mapped[str] = mapped_column(String(10), nullable=False, index=True, comment="HTTP 方法")
    path: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="请求路径")
    module: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True, comment="业务模块")
    action: Mapped[str] = mapped_column(String(30), nullable=False, index=True, comment="动作：create/update/delete/export/…")
    summary: Mapped[str] = mapped_column(String(255), nullable=False, comment="摘要")
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200, comment="HTTP 状态码")
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否成功（<400）")
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="客户端 IP")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="补充信息（查询串等，不含敏感体）")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=now,
        index=True,
        comment="发生时间（东八区墙钟）",
    )
