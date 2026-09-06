"""
总成月核价结果主表

一行 = 一个 BOM 核价根 × 年 × 月 × 范围。
月总账 total_amount 不含间接；should_cost = total_amount；grand_total = 月总账 + 间接。
不认 stamping_supplier。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin

if TYPE_CHECKING:
    from app.models.costing.assembly_cost_indirect import AssemblyCostIndirect
    from app.models.costing.assembly_cost_item import AssemblyCostItem


class AssemblyCost(AuditUserMixin, Base):
    """总成月核价结果"""

    __tablename__ = "costing_assembly_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    items: Mapped[list[AssemblyCostItem]] = relationship(
        "AssemblyCostItem",
        back_populates="assembly_cost",
        cascade="all, delete-orphan",
        order_by="AssemblyCostItem.sort_no, AssemblyCostItem.id",
    )
    indirects: Mapped[list[AssemblyCostIndirect]] = relationship(
        "AssemblyCostIndirect",
        back_populates="assembly_cost",
        cascade="all, delete-orphan",
        order_by="AssemblyCostIndirect.sort_no, AssemblyCostIndirect.id",
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="计算年度")
    month: Mapped[int] = mapped_column(Integer, nullable=False, comment="计算月份")
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目/车型")
    bom_version: Mapped[str] = mapped_column(String(20), nullable=False, comment="BOM 版本")

    source_node_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="核价根 bom_nodes.id"
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_tree_root: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parent_node_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    root_part_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    root_part_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    procurement_object_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    object_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)

    part_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="本卡根零件号")
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="本卡根名称")
    supply_qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1"),
        comment="单车用量",
    )
    bom_snapshot_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="来源 bom_snapshots.id"
    )
    sketch_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="零件图册")

    stamping_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="① 冲压小计"
    )
    purchased_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="② 年度价/外购小计"
    )
    bundle_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="③ 一口价小计"
    )
    material_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="材料合计=①+②+③"
    )
    welding_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="④ 焊接费"
    )
    welding_other_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="⑤ 焊接其它费用"
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="月总账（不含间接）"
    )
    should_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="应成本=月总账"
    )
    vendor_quote: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    gap_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    unit_transport_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="I1 单件运输费"
    )
    warehouse_bundling_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0"),
        comment="I2 仓储费+捆包费",
    )
    finished_finance_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="I3 财务费"
    )
    finished_management_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="I4 管理费"
    )
    finished_scrap_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="I5 报废费用"
    )
    finished_pretax_profit_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="I6 税前利润"
    )
    gauge_alloc_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="I7 检具分摊费"
    )
    fixture_alloc_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="I8 器具分摊费"
    )
    allocation_fee_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="分摊合计=I7+I8"
    )
    indirect_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="间接费用合计"
    )
    grand_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0"), comment="总费用=月总账+间接"
    )

    finance_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), nullable=False, default=Decimal("0.02"), comment="财务费率快照"
    )
    management_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), nullable=False, default=Decimal("0.02"), comment="管理费率快照"
    )
    scrap_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), nullable=False, default=Decimal("0.003"), comment="报废费率快照"
    )
    pretax_profit_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), nullable=False, default=Decimal("0.02"), comment="税前利润率快照"
    )

    welding_fee_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="溯源 bom_welding_fees.id（财务读 level=0）"
    )
    welding_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="焊接摘要")

    calc_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ok",
        comment="ok / partial / failed",
    )
    missing_leaf_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="材料缺价叶子数"
    )
    calc_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="计算说明")
    formula_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="公式版本"
    )
    calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="计算时间"
    )
    calc_batch_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="计算批次号"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    audit_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending / approved",
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
            "month",
            "location",
            "vehicle_model",
            "bom_version",
            "source_node_id",
            name="uix_assembly_cost_scope_node",
        ),
        Index("ix_assembly_cost_year_month", "year", "month"),
        Index("ix_assembly_cost_location", "location"),
        Index("ix_assembly_cost_vehicle", "vehicle_model"),
        Index("ix_assembly_cost_part", "part_number"),
        Index("ix_assembly_cost_calc_status", "calc_status"),
        Index("ix_assembly_cost_audit_status", "audit_status"),
        Index("ix_assembly_cost_batch", "calc_batch_id"),
        Index(
            "ix_assembly_cost_scope_level",
            "year",
            "month",
            "location",
            "vehicle_model",
            "bom_version",
            "level",
        ),
        Index(
            "ix_assembly_cost_scope_tree_root",
            "year",
            "month",
            "location",
            "vehicle_model",
            "bom_version",
            "is_tree_root",
        ),
    )
