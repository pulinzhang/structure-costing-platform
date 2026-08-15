"""
冲压加工费工序分项子表

记录各工序单价计算依据，便于查看与导出溯源。
主表 stamping_process_fees 一行对应多行本表。
"""

from decimal import Decimal
from sqlalchemy import (

    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,)
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.database import Base


class StampingProcessFeeItem(Base):
    """零件加工费 — 单道工序计算依据"""

    __tablename__ = "stamping_process_fee_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fee_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stamping_process_fees.id", ondelete="CASCADE"),
        nullable=False,
        comment="加工费主表 id",
    )

    source_process_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="来源工序表 id")
    process_seq: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="工序序号")
    process_order: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="工序顺序")
    process_code: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="工序代码")

    original_tonnage: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="工序原始吨位(T)")
    resolved_tonnage: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="实际用于计价的吨位(T)")
    tonnage_source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="self",
        comment="吨位来源：self=自有 / inherited=继承上一件 / swing_shear=摆剪不计费",
    )
    inherited_from_part_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="继承来源零件 id")
    inherited_from_part_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="继承来源零件号"
    )
    inherited_from_process_seq: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="继承来源工序序号"
    )
    inherited_from_process_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="继承来源工序代码"
    )

    cost_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, comment="费用比例")
    tonnage_price_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="冲次单价表 id")
    price_per_stroke: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True, comment="冲次单价(元)"
    )
    line_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=0, comment="本序加工费(元)"
    )
    basis_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="人可读计算依据摘要")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="工序备注快照")

    fee = relationship(
        "StampingProcessFee",
        back_populates="process_items",
    )

    __table_args__ = (
        Index("ix_stamping_process_fee_item_fee_id", "fee_id"),
        Index(
            "ix_stamping_process_fee_item_fee_order",
            "fee_id",
            "process_order",
        ),
    )
