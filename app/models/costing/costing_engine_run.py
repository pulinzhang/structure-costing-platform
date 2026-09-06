"""月度智能自动核价引擎 — Run 账本。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin

if TYPE_CHECKING:
    from app.models.costing.costing_engine_run_step import CostingEngineRunStep


class CostingEngineRun(AuditUserMixin, Base):
    """一次基地+年+月的引擎编排记录。"""

    __tablename__ = "costing_engine_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="生产基地")
    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="核价年度")
    month: Mapped[int] = mapped_column(Integer, nullable=False, comment="核价月份")

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        comment="blocked / running / succeeded / partial / failed",
    )
    task_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="父 AsyncTask ID"
    )

    gate_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Phase1 门禁快照"
    )
    plan_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="工厂 / L0Scope / 年度补算清单"
    )
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="终态摘要"
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="结束时间"
    )

    steps: Mapped[list[CostingEngineRunStep]] = relationship(
        "CostingEngineRunStep",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="CostingEngineRunStep.id",
    )

    __table_args__ = (
        Index("ix_costing_engine_run_key", "location", "year", "month"),
        Index("ix_costing_engine_run_status", "status"),
        Index("ix_costing_engine_run_task_id", "task_id"),
        Index("ix_costing_engine_run_started_at", "started_at"),
    )
