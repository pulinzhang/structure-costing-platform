"""
BOM 焊接费明细子表

主表 bom_welding_fees 一行对应多行本表（按拆解工艺明细计费）。
"""

from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BomWeldingFeeItem(Base):
    """焊接费 — 单条工艺明细计费依据"""

    __tablename__ = "bom_welding_fee_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fee_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bom_welding_fees.id", ondelete="CASCADE"),
        nullable=False,
        comment="焊接费主表 id",
    )

    line_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="明细序号")
    process_token: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="原文工艺词"
    )
    standard_process_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="标准工艺名称"
    )
    process_qty: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, comment="过程量（未乘装配用量）"
    )
    process_qty_unit: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="过程量单位"
    )
    unit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="匹配到的工费单价(元)"
    )
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="单价单位")
    line_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True, comment="本行焊接费(元)=过程量×单价"
    )
    match_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unmapped",
        comment="匹配状态：matched / missing_price / unmapped",
    )
    source_breakdown_line_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="来源拆解明细 id"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    fee = relationship("BomWeldingFee", back_populates="items")

    __table_args__ = (
        Index("ix_bom_welding_fee_item_fee_id", "fee_id"),
        Index(
            "ix_bom_welding_fee_item_fee_line",
            "fee_id",
            "line_no",
        ),
    )
