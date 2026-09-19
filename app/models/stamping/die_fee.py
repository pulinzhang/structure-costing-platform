"""冲压年度模具费结果主表。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin

if TYPE_CHECKING:
    from app.models.stamping.die_fee_item import StampingDieFeeItem


class StampingDieFee(AuditUserMixin, Base):
    """年度模具费零件结果（系统费 + 调整金额）。"""

    __tablename__ = "stamping_die_fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    items: Mapped[list[StampingDieFeeItem]] = relationship(
        "StampingDieFeeItem",
        back_populates="fee",
        cascade="all, delete-orphan",
        order_by="StampingDieFeeItem.process_order, StampingDieFeeItem.id",
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="计算年度")
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目")
    stamping_supplier: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="冲压供应商（从布点快照）"
    )
    version: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="版本（从布点快照）"
    )
    part_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="零件号")

    source_die_part_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("stamping_die_parts.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=True,
        comment="来源布点主表 id",
    )
    seq_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="序号")
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="零件名称")
    material: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="材质")
    thickness: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True, comment="料厚(mm)"
    )
    part_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="零件重量(kg)"
    )
    die_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="模具类型")
    die_method: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="模具方式")
    production_mode: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="生产方式"
    )
    part_grade: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="零件等级")
    excel_filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="来源Excel文件名"
    )

    price_kind: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="progressive / steel_plate"
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, comment="万元/吨")
    allocation_qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, comment="万台")
    die_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, comment="系统模具费(元)"
    )
    adjustment_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="调整金额(元)"
    )
    final_die_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, comment="最终模具费(元)"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="调整说明")

    audit_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending / approved / rejected",
    )
    audited_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    reverse_audited_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reverse_audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reverse_audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "year",
            "location",
            "vehicle_model",
            "part_number",
            name="uix_stamping_die_fee_unique_key",
        ),
        Index("ix_stamping_die_fee_year", "year"),
        Index("ix_stamping_die_fee_location_vehicle", "location", "vehicle_model"),
        Index("ix_stamping_die_fee_part_number", "part_number"),
        Index("ix_stamping_die_fee_audit_status", "audit_status"),
        Index("ix_stamping_die_fee_source_die_part_id", "source_die_part_id"),
    )
