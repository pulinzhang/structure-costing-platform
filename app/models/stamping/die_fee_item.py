"""冲压年度模具费各序子表。"""

from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StampingDieFeeItem(Base):
    """零件模具费 — 单道工序。"""

    __tablename__ = "stamping_die_fee_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fee_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stamping_die_fees.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_die_process_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="来源布点工序 id（软指针；再导会删插工序，不加 FK）",
    )
    process_seq: Mapped[str] = mapped_column(String(20), nullable=False)
    process_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    process_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_weight_t: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    alloc_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    die_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    allocation_qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    price_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    line_die_fee: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    basis_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    fee = relationship("StampingDieFee", back_populates="items")

    __table_args__ = (
        UniqueConstraint("fee_id", "process_seq", name="uix_stamping_die_fee_item_seq"),
        Index("ix_stamping_die_fee_item_fee_id", "fee_id"),
        Index("ix_stamping_die_fee_item_fee_order", "fee_id", "process_order"),
    )
