"""L0 月度预聚合事实表（B.7 #14）。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class LlmMonthlyCostSummary(AuditUserMixin, Base):
    """按月/基地/车型/BOM 预聚合；ETL 每日刷新，查询优先走此表。"""

    __tablename__ = "llm_monthly_cost_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False)
    bom_version: Mapped[str] = mapped_column(String(20), nullable=False)

    l0_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ok_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    partial_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_price_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="缺价行数（grand_total=0）"
    )

    grand_total_sum: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    total_amount_sum: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    indirect_amount_sum: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    stamping_amount_sum: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    purchased_amount_sum: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    bundle_amount_sum: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    welding_amount_sum: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    welding_other_amount_sum: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), nullable=False, default=0
    )

    __table_args__ = (
        UniqueConstraint(
            "year",
            "month",
            "location",
            "vehicle_model",
            "bom_version",
            name="uix_llm_monthly_cost_summary_scope",
        ),
        Index("ix_llm_monthly_cost_summary_ym", "year", "month"),
        Index("ix_llm_monthly_cost_summary_location", "location"),
    )
