"""ORM 审计字段 Mixin：创建/修改时间与操作人。"""

from sqlalchemy import Column, DateTime, String

from app.common.timezone import now


class AuditUserMixin:
    """业务表统一审计字段（子类勿再重复定义）。"""

    created_at = Column(DateTime, default=now, nullable=False, comment="创建时间（东八区墙钟）")
    created_by = Column(String(50), nullable=True, comment="创建人")
    updated_at = Column(
        DateTime,
        default=now,
        onupdate=now,
        nullable=False,
        comment="最后修改时间（东八区墙钟）",
    )
    updated_by = Column(String(50), nullable=True, comment="最后修改人")
