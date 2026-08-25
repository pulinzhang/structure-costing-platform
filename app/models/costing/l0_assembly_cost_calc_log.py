"""成品月核价 — 计算任务日志。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class L0AssemblyCostCalcLog(AuditUserMixin, Base):
    """成品月核价计算日志（scope 锁 + 历史）。"""

    __tablename__ = "costing_l0_assembly_cost_calc_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False)
    bom_version: Mapped[str] = mapped_column(String(20), nullable=False)

    calc_batch_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="processing",
        comment="processing / success / partial / failed",
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    l0_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ok_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    partial_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_approved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index(
            "ix_l0_assembly_calc_log_scope",
            "year",
            "month",
            "location",
            "vehicle_model",
            "bom_version",
        ),
        Index("ix_l0_assembly_calc_log_status", "status"),
    )
