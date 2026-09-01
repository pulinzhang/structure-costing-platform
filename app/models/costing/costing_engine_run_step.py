"""月度智能自动核价引擎 — Run 步骤。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.costing.costing_engine_run import CostingEngineRun


class CostingEngineRunStep(Base):
    """引擎 Run 内单个 stage/scope 步骤。"""

    __tablename__ = "costing_engine_run_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("costing_engine_runs.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属 Run",
    )

    stage: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        comment=(
            "annual_process_fee / annual_welding_breakdown / annual_welding_fee "
            "/ steel / part_cost / assembly / export"
        ),
    )
    scope_key: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="",
        comment="工厂名，或 vehicle_model|bom_version",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending / running / succeeded / skipped / failed",
    )

    child_task_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="可选子任务引用（首版空）"
    )
    child_log_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="可选业务日志 ID"
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="步骤说明/错误")
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="步骤指标"
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    run: Mapped[CostingEngineRun] = relationship(
        "CostingEngineRun",
        back_populates="steps",
    )

    __table_args__ = (
        Index("ix_costing_engine_step_run", "run_id"),
        Index("ix_costing_engine_step_stage", "stage"),
        Index("ix_costing_engine_step_status", "status"),
    )
