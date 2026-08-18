"""
BOM L0焊接费（完工产品 / 供货总成）结果表

按年度 + 基地 + 车型 + BOM 版本 + L0 拆解节点维度存储。
仅计完工产品（level=0）过程量 × 分年焊接单价；下级工艺不计费。
审核锁定：audit_status == 'approved' 时禁止重算覆盖 / 删除；须先反审核。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.audit_mixin import AuditUserMixin

if TYPE_CHECKING:
    from app.models.bom_l0_welding_fee_item import BomL0WeldingFeeItem


class BomL0WeldingFee(AuditUserMixin, Base):
    """BOM 焊接费计算结果（L0 零件一行）"""

    __tablename__ = "bom_l0_welding_fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    items: Mapped[List["BomL0WeldingFeeItem"]] = relationship(
        "BomL0WeldingFeeItem",
        back_populates="fee",
        cascade="all, delete-orphan",
        order_by="BomL0WeldingFeeItem.line_no, BomL0WeldingFeeItem.id",
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="计算年度")
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="车型")
    bom_version: Mapped[str] = mapped_column(String(20), nullable=False, comment="材料清单版本")

    source_breakdown_node_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="来源焊接工艺拆解主表 id（L0）",
    )
    part_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="零件号")
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="零件名称")
    customer_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="顾客名称"
    )
    weld_info_raw: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="计算时快照的焊接信息原文（来自拆解 L0）",
    )

    process_line_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="工艺明细行数"
    )
    matched_line_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已匹配单价行数"
    )
    missing_price_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="缺单价行数"
    )
    total_l0_welding_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=0,
        comment="焊接费合计(元)",
    )

    calc_batch_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="计算批次号"
    )
    calc_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ok",
        comment="计算状态：ok / partial / failed",
    )
    calc_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="计算说明/失败原因"
    )

    audit_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="审核状态：pending=待审，approved=已通过，rejected=已驳回",
    )
    audited_by: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最近一次审核人")
    audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近一次审核时间")
    audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近一次审核意见")
    reverse_audited_by: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="反审核人")
    reverse_audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="反审核时间")
    reverse_audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="反审核原因")

    __table_args__ = (
        UniqueConstraint(
            "year",
            "location",
            "vehicle_model",
            "bom_version",
            "source_breakdown_node_id",
            name="uix_bom_l0_welding_fee_scope_node",
        ),
        Index("ix_bom_l0_welding_fee_year", "year"),
        Index("ix_bom_l0_welding_fee_location", "location"),
        Index("ix_bom_l0_welding_fee_vehicle_model", "vehicle_model"),
        Index("ix_bom_l0_welding_fee_bom_version", "bom_version"),
        Index("ix_bom_l0_welding_fee_part_number", "part_number"),
        Index("ix_bom_l0_welding_fee_audit_status", "audit_status"),
        Index("ix_bom_l0_welding_fee_calc_status", "calc_status"),
        Index(
            "ix_bom_l0_welding_fee_scope",
            "year",
            "location",
            "vehicle_model",
            "bom_version",
        ),
    )
