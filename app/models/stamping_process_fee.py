"""
冲压加工费结果表
按年度 + 基地 + 冲压工厂 + 零件维度存储加工费计算结果

零件主表字段在计算时快照写入，便于列表展示与溯源（不依赖原表后续变更）。

审核锁定：
  audit_status == 'approved' 时，禁止手工调整、删除、重算覆盖；
  须先反审核为 pending。
"""

from typing import List

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Text,
    DateTime,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, relationship

from app.database import Base
from app.models.audit_mixin import AuditUserMixin


class StampingProcessFee(AuditUserMixin, Base):
    """冲压零件加工费计算结果"""

    __tablename__ = "stamping_process_fees"

    id = Column(Integer, primary_key=True, autoincrement=True)

    process_items: Mapped[List["StampingProcessFeeItem"]] = relationship(
        "StampingProcessFeeItem",
        back_populates="fee",
        cascade="all, delete-orphan",
        order_by="StampingProcessFeeItem.process_order, StampingProcessFeeItem.id",
    )

    year = Column(Integer, nullable=False, comment="计算年度")
    location = Column(String(50), nullable=False, comment="采购基地")
    stamping_supplier = Column(String(50), nullable=False, comment="冲压工厂")
    vehicle_model = Column(String(50), nullable=False, comment="车型")
    version = Column(String(20), nullable=False, comment="版本")

    # —— 零件主表快照（来自 stamping_parts）——
    source_part_id = Column(Integer, nullable=True, comment="来源零件主表 id")
    seq_no = Column(Integer, nullable=True, comment="序号")
    part_number = Column(String(50), nullable=False, comment="零件号")
    part_name = Column(String(200), nullable=True, comment="零件名称")

    # 材料信息
    material = Column(String(50), nullable=True, comment="材质")
    thickness = Column(Numeric(10, 4), nullable=True, comment="料厚(mm)")
    part_weight = Column(Numeric(12, 4), nullable=True, comment="零件重量(kg)")

    # 料片尺寸
    sheet_length = Column(Numeric(10, 2), nullable=True, comment="料片长/卷料宽(mm)")
    sheet_width = Column(Numeric(10, 2), nullable=True, comment="料片宽/卷料步距(mm)")

    # 生产信息
    parts_per_sheet = Column(Integer, nullable=True, comment="可制件数")
    sheet_type = Column(String(50), nullable=True, comment="料片式样")

    # 工艺信息
    die_type = Column(String(50), nullable=True, comment="模具类型")
    process_method = Column(String(50), nullable=True, comment="工艺方法")
    automation = Column(String(20), nullable=True, comment="自动化")

    # 扩展 / 溯源
    part_remark = Column(Text, nullable=True, comment="零件主表备注快照")
    sketch_url = Column(
        String(500), nullable=True, comment="零件简图URL（相对路径）"
    )
    excel_filename = Column(
        String(255), nullable=True, comment="来源Excel文件名"
    )

    # 系统计算值；算不出时可为空，由手工调整单价补齐
    processing_fee = Column(
        Numeric(12, 3), nullable=True, comment="系统计算加工费(元)"
    )
    process_count = Column(Integer, nullable=False, default=0, comment="参与汇总的工序数")
    manual_unit_price = Column(
        Numeric(12, 3), nullable=True, comment="手工调整单价(元)"
    )
    final_processing_fee = Column(
        Numeric(12, 3), nullable=True, comment="最终加工费(元)"
    )
    calc_fail_reason = Column(Text, nullable=True, comment="计算失败原因")
    remark = Column(Text, nullable=True, comment="备注（手工调整理由等）")

    # 审核锁定 + 反审核留痕
    audit_status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="审核状态：pending=待审，approved=已通过，rejected=已驳回",
    )
    audited_by = Column(String(50), nullable=True, comment="最近一次审核人")
    audited_at = Column(DateTime, nullable=True, comment="最近一次审核时间")
    audit_remark = Column(Text, nullable=True, comment="最近一次审核意见")
    reverse_audited_by = Column(String(50), nullable=True, comment="反审核人")
    reverse_audited_at = Column(DateTime, nullable=True, comment="反审核时间")
    reverse_audit_remark = Column(Text, nullable=True, comment="反审核原因")

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
