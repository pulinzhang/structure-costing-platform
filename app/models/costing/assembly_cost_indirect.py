"""成品月核价 — 间接费用一一单列。"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.costing.assembly_cost import AssemblyCost


class AssemblyCostIndirect(Base):
    """间接费用行（I1～I8）。"""

    __tablename__ = "costing_assembly_cost_indirects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assembly_cost_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("costing_assembly_costs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assembly_cost: Mapped[AssemblyCost] = relationship("AssemblyCost", back_populates="indirects")

    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="间接项代码")
    label: Mapped[str] = mapped_column(String(100), nullable=False, comment="展示名")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    base_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    sort_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "assembly_cost_id",
            "code",
            name="uix_assembly_cost_indirect_code",
        ),
    )
