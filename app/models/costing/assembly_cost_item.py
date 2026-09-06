"""成品月核价 — 材料 / 一口价 / 剪枝明细行。"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.costing.assembly_cost import AssemblyCost


class AssemblyCostItem(Base):
    """材料明细（含 skipped_by_bundle）。"""

    __tablename__ = "costing_assembly_cost_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assembly_cost_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("costing_assembly_costs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assembly_cost: Mapped[AssemblyCost] = relationship("AssemblyCost", back_populates="items")

    node_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bom_node_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    part_number: Mapped[str] = mapped_column(String(50), nullable=False)
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    node_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    supply_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="供货类型快照"
    )
    cost_source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="stamping / annual / bundle / skipped_by_bundle / missing",
    )
    match_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    effective_qty: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), nullable=False, default=Decimal("1")
    )
    line_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    sort_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "assembly_cost_id",
            "sort_no",
            name="uix_assembly_cost_item_line",
        ),
    )
