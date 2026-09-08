"""
冲压加工费结果表
按年度 + 基地 + 冲压工厂 + 零件维度存储加工费计算结果

零件主表字段在计算时快照写入，便于列表展示与溯源（不依赖原表后续变更）。

审核锁定：
  audit_status == 'approved' 时，禁止编辑其它费用、删除、重算覆盖；
  须先反审核为 pending。
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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin

if TYPE_CHECKING:
    from app.models.stamping.process_fee_item import StampingProcessFeeItem


class StampingProcessFee(AuditUserMixin, Base):
    """冲压零件加工费计算结果"""

    __tablename__ = "stamping_process_fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    process_items: Mapped[list[StampingProcessFeeItem]] = relationship(
        "StampingProcessFeeItem",
        back_populates="fee",
        cascade="all, delete-orphan",
        order_by="StampingProcessFeeItem.process_order, StampingProcessFeeItem.id",
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="计算年度")
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    stamping_supplier: Mapped[str] = mapped_column(String(100), nullable=False, comment="冲压工厂")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="车型")
    version: Mapped[str] = mapped_column(String(20), nullable=False, comment="版本")

    # —— 零件主表快照（来自 stamping_parts）——
    source_part_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="来源零件主表 id"
    )
    seq_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="序号")
    part_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="零件号")
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="零件名称")

    # 材料信息
    material: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="材质")
    thickness: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True, comment="料厚(mm)"
    )
    part_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="零件重量(kg)"
    )

    # 料片尺寸
    sheet_length: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="料片长/卷料宽(mm)"
    )
    sheet_width: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="料片宽/卷料步距(mm)"
    )

    # 生产信息
    # 一张钢板/料片单独冲本零件可出的件数（快照自零件主表）
    # 例：1出2记2；左右共模同冲按单侧零件计则为2。非「利用率百分比」。
    parts_per_sheet: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "可制件数：一张钢板/料片单独冲本零件可出的件数" "（例：1出2记2；左右共模按单侧计则为2）"
        ),
    )
    sheet_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="料片式样")

    # 工艺信息
    die_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="模具类型")
    process_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="工艺方法"
    )
    automation: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="自动化：工艺文件原文快照（如自动/手动/半自动），非布尔是/否",
    )

    # 扩展 / 溯源
    part_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="零件主表备注快照")
    sketch_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="零件简图URL（相对路径）"
    )
    excel_filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="来源Excel文件名"
    )
    is_tailor_welded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否拼焊件（计算时快照自零件主表；拼焊费录入其它费用）",
    )

    # 系统计算值；算不出时可为空，由其它费用补齐
    processing_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True, comment="系统计算加工费(元)"
    )
    process_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="参与汇总的工序数"
    )
    other_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True, comment="其它费用(元)，如拼焊费；可正可负"
    )
    final_processing_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True, comment="确认单价(元) = 系统计算 + 其它费用"
    )
    calc_fail_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="计算失败原因"
    )
    remark: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="备注（其它费用说明等）"
    )

    # 审核锁定 + 反审核留痕
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
        Index("ix_stamping_process_fee_year", "year"),
        Index("ix_stamping_process_fee_location", "location"),
        Index("ix_stamping_process_fee_part_number", "part_number"),
        Index(
            "ix_stamping_process_fee_year_location",
            "year",
            "location",
        ),
        Index("ix_stamping_process_fee_supplier", "stamping_supplier"),
        Index("ix_stamping_process_fee_audit_status", "audit_status"),
        Index("ix_stamping_process_fee_material", "material"),
        Index("ix_stamping_process_fee_is_tailor_welded", "is_tailor_welded"),
        UniqueConstraint(
            "year",
            "location",
            "stamping_supplier",
            "vehicle_model",
            "version",
            "part_number",
            name="uix_stamping_process_fee_unique_key",
        ),
    )
