"""
冲压件工艺数据模型
使用主从表结构存储冲压件工艺信息（零件主表 + 工序子表）
"""

from decimal import Decimal
from datetime import datetime
from typing import List
from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, Text, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped

from app.database import Base


class StampingPart(Base):
    """
    冲压件主表 - 存储零件基本信息
    vehicle_model + version 直接存于此表，不单独建车型表
    """
    __tablename__ = "stamping_parts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 车型信息（直接存储，不关联车型表）
    vehicle_model = Column(String(50), nullable=False, comment="车型")
    version = Column(String(20), nullable=False, comment="版本")

    # 序号和基本信息
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
    tonnage = Column(Numeric(10, 2), nullable=True, comment="冲压设备吨位(T)")
    die_type = Column(String(50), nullable=True, comment="模具类型")
    process_method = Column(String(50), nullable=True, comment="工艺方法")
    automation = Column(String(20), nullable=True, comment="自动化")

    # 扩展信息
    remark = Column(Text, nullable=True, comment="备注")
    sketch_url = Column(String(500), nullable=True, comment="零件简图URL（相对于上传目录，格式：车型/日期/零件号.png）")

    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联
    processes: Mapped[List["StampingProcess"]] = relationship(
        "StampingProcess",
        back_populates="part",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_part_vehicle_model", "vehicle_model"),
        Index("ix_part_version", "version"),
        Index("ix_part_number", "part_number"),
        # 零件号全局唯一，不允许重复插入
        UniqueConstraint(
            "part_number",
            name="uix_part_number_unique"
        ),
    )


class StampingProcess(Base):
    """
    冲压工序子表 - 存储零件的冲压工序详情
    """
    __tablename__ = "stamping_processes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(Integer, ForeignKey("stamping_parts.id", ondelete="CASCADE"), nullable=False)

    # 工序信息
    process_seq = Column(String(20), nullable=False, comment="工序序号(如OP10)")
    process_order = Column(Integer, nullable=False, default=1, comment="零件内工序顺序(从1开始)")
    process_code = Column(String(50), nullable=True, comment="工序代码(如DR/TR+PI)")
    die_sets = Column(Integer, nullable=True, default=1, comment="套数")

     # 设备信息
    tonnage = Column(Integer, nullable=True, comment="设备吨位(T)")

    # 费用比例（用于共模分摊，如左右件各占50%则填0.5）
    cost_ratio = Column(Numeric(5, 2), nullable=False, default=Decimal("1.00"), comment="单次冲压费用比例")

    # 扩展信息
    remark = Column(Text, nullable=True, comment="备注")

    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联
    part: Mapped["StampingPart"] = relationship("StampingPart", back_populates="processes")

    __table_args__ = (
        Index("ix_process_part_id", "part_id"),
        Index("ix_process_seq", "process_seq"),
    )
