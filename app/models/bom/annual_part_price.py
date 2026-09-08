"""
BOM 年度零件价数据模型（外购 + L1 一口价合并）

审核锁定：
  audit_status == 'approved' 时，禁止修改、删除、导入覆盖；
  须先反审核为 pending。

唯一键：(location, year, part_number) — 无车型。
核价语义由 BOM 节点形态决定，本表只存单价。
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class BomAnnualPartPrice(AuditUserMixin, Base):
    """BOM 年度零件价表（按基地 + 年 + 零件号）"""

    __tablename__ = "bom_annual_part_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    location: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="采购基地，例：青岛、芜湖、大连、鄂尔多斯",
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="定价年度（如 2026）")

    part_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="零件号（取价匹配主键）",
    )

    part_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="零件名称（展示 / 导入校验）",
    )

    specification: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="规格（展示 / 当档，不参与取价）",
    )

    purchase_unit: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="采购单位（报价包装，如打、瓶）",
    )

    purchase_unit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="采购单价(元/采购单位)，Numeric(12,4)",
    )

    conversion_factor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="转换系数，正整数，默认1；1采购单位=N核价单位；核价单价=采购单价/N",
    )

    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pcs",
        comment="核价单位，应对齐 BOM qty_unit，默认 pcs",
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="核价单价(元/核价单位)，Numeric(12,4) 固定4位小数",
    )

    supply_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="原供货类型原文，例：沿用、标准件、胶块、分总成",
    )

    supplier_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="供应商（展示，不参与计算）",
    )

    remark: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="备注",
    )

    audit_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="审核状态：pending=待审，approved=已通过，rejected=已驳回",
    )
    audited_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="最近一次审核人"
    )
    audited_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最近一次审核时间"
    )
    audit_remark: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="最近一次审核意见"
    )
    reverse_audited_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="反审核人"
    )
    reverse_audited_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="反审核时间"
    )
    reverse_audit_remark: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="反审核原因"
    )

    __table_args__ = (
        Index("ix_annual_part_price_location", "location"),
        Index("ix_annual_part_price_year", "year"),
        Index("ix_annual_part_price_part_number", "part_number"),
        Index("ix_annual_part_price_supply_type", "supply_type"),
        Index("ix_annual_part_price_audit_status", "audit_status"),
        Index("ix_annual_part_price_location_year", "location", "year"),
        UniqueConstraint(
            "location",
            "year",
            "part_number",
            name="uix_annual_part_price_location_year_part",
        ),
    )
