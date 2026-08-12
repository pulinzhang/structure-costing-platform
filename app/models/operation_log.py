"""操作审计日志（主库）。"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.common.timezone import now
from app.database import Base


class OperationLog(Base):
    """业务操作审计日志：写操作 + 导出。"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True, comment="操作人用户 ID")
    username = Column(String(50), nullable=True, index=True, comment="登录账号")
    operator_name = Column(String(50), nullable=True, comment="展示名")
    method = Column(String(10), nullable=False, index=True, comment="HTTP 方法")
    path = Column(String(255), nullable=False, index=True, comment="请求路径")
    module = Column(String(50), nullable=True, index=True, comment="业务模块")
    action = Column(String(30), nullable=False, index=True, comment="动作：create/update/delete/export/…")
    summary = Column(String(255), nullable=False, comment="摘要")
    status_code = Column(Integer, nullable=False, default=200, comment="HTTP 状态码")
    success = Column(Boolean, nullable=False, default=True, comment="是否成功（<400）")
    client_ip = Column(String(64), nullable=True, comment="客户端 IP")
    detail = Column(Text, nullable=True, comment="补充信息（查询串等，不含敏感体）")
    created_at = Column(
        DateTime,
        nullable=False,
        default=now,
        index=True,
        comment="发生时间（东八区墙钟）",
    )
