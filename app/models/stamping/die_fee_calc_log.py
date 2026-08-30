"""冲压年度模具费计算批次日志。"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class StampingDieFeeCalcLog(AuditUserMixin, Base):
    """计算锁范围：year + location + vehicle_model。"""

    __tablename__ = "stamping_die_fee_calc_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    calc_batch_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="failed",
        comment="processing / success / failed",
    )
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_no_die_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detail_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index("ix_sdf_calc_log_batch", "calc_batch_id"),
        Index("ix_sdf_calc_log_year", "year"),
        Index("ix_sdf_calc_log_location", "location"),
        Index("ix_sdf_calc_log_status", "status"),
        Index("ix_sdf_calc_log_started_at", "started_at"),
        Index(
            "uq_sdf_calc_processing",
            "year",
            "location",
            "vehicle_model",
            unique=True,
            sqlite_where=text("status = 'processing'"),
        ),
    )
