"""ORM 审计字段 Mixin：创建/修改时间与操作人。"""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.timezone import now


class AuditUserMixin:
    """业务表统一审计字段（子类勿再重复定义）。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=now, nullable=False, comment="创建时间（东八区墙钟）"
    )
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="创建人")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        nullable=False,
        comment="最后修改时间（东八区墙钟）",
    )
    updated_by: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最后修改人")
