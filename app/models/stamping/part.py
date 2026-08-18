"""
冲压件工艺数据模型
使用主从表结构存储冲压件工艺信息（零件主表 + 工序子表）
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    Boolean,
    ForeignKey,
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
    from app.models.stamping.tailor_weld_blank import StampingTailorWeldBlank


class StampingPart(AuditUserMixin, Base):
    """
    冲压件主表 - 存储零件基本信息
    vehicle_model + version 直接存于此表，不单独建车型表

    拼焊总成：is_tailor_welded=True，各片子片见 StampingTailorWeldBlank；
    工序仍挂本表（StampingProcess），核价时按子片算后汇总到父。
    """
    __tablename__ = "stamping_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 【基地与归属维度】
    location: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="采购基地，例： 大连、芜湖、鄂尔多斯、青岛"
    )
    # 【供应商维度】
    stamping_supplier: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="冲压供应商，例：安庆常庆汽车部件有限公司"
    )
    # 车型信息（直接存储，不关联车型表）
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="车型")
    version: Mapped[str] = mapped_column(String(20), nullable=False, comment="版本")

    # 序号和基本信息
    seq_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="序号")
    part_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="零件号")
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="零件名称")

    # 拼焊标识（总成）；子片材料侧见 stamping_tailor_weld_blanks
    is_tailor_welded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否拼焊件（对外总成）；默认否。为是时各片材料在子表，工序仍挂本表",
    )

    # 材料信息（普通件使用；拼焊总成可空，以各子片为准）
    material: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="材质")
    thickness: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True, comment="料厚(mm)")
    part_weight: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True, comment="零件重量(kg)")

    # 料片尺寸
    sheet_length: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="料片长/卷料宽(mm)")
    sheet_width: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="料片宽/卷料步距(mm)")

    # 生产信息
    # parts_per_sheet：一张钢板/料片单独冲压「本零件」时可出的件数。
    # 例：1 张料出 2 件 → 2；出 1 件 → 1；左右件共模同冲时按单侧零件计则为 2。
    parts_per_sheet: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "可制件数：一张钢板/料片单独冲本零件可出的件数"
            "（例：1出2记2；左右共模按单侧计则为2）"
        ),
    )
    sheet_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="料片式样")

    # 工艺信息
    die_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="模具类型")
    process_method: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="工艺方法")
    automation: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="自动化：工艺文件原文（如自动/手动/半自动），非布尔是/否",
    )

    # 扩展信息
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    sketch_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="零件简图URL（相对于上传目录，格式：车型/日期/零件号.png）")

    # 【防扯皮与溯源铁证字段（与 BOM / 钢价对齐：文件 + 表页 + 行 + 零件号列）】
    excel_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="来源Excel文件名，例：2025年11月马钢测试.xlsx",
    )
    excel_sheet_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="来源工作表名。例：工艺卡",
    )
    excel_row: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="来源 Excel 行号（1-based，与 Excel 界面行号一致）",
    )
    excel_part_col: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="零件号所在列号（1-based，对应表头解析出的 part_no 列）",
    )

    # 关联
    processes: Mapped[List["StampingProcess"]] = relationship(
        "StampingProcess",
        back_populates="part",
        cascade="all, delete-orphan"
    )
    tailor_weld_blanks: Mapped[List["StampingTailorWeldBlank"]] = relationship(
        "StampingTailorWeldBlank",
        back_populates="part",
        cascade="all, delete-orphan",
        order_by="StampingTailorWeldBlank.blank_seq",
    )

    __table_args__ = (
        Index("ix_part_location_supplier_model_version_number",
              "location", "stamping_supplier", "vehicle_model", "version", "part_number"),
        Index("ix_part_vehicle_model", "vehicle_model"),
        Index("ix_part_version", "version"),
        Index("ix_part_number", "part_number"),
        Index("ix_part_is_tailor_welded", "is_tailor_welded"),
        # 唯一键：基地 + 供应商 + 车型 + 版本 + 零件号
        UniqueConstraint(
            "location", "stamping_supplier", "vehicle_model", "version", "part_number",
            name="uix_part_unique_key"
        ),
    )


class StampingProcess(AuditUserMixin, Base):
    """
    冲压工序子表 - 存储零件的冲压工序详情
    """
    __tablename__ = "stamping_processes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(Integer, ForeignKey("stamping_parts.id", ondelete="CASCADE"), nullable=False)

    # 工序信息
    process_seq: Mapped[str] = mapped_column(String(20), nullable=False, comment="工序序号(如OP10)")
    process_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="零件内工序顺序(从1开始)")
    process_code: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="工序代码(如DR/TR+PI)")
    die_sets: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1, comment="套数")

     # 设备信息
    tonnage: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="设备吨位(T)")

    # 费用比例（用于共模分摊，如左右件各占50%则填0.5）
    cost_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("1.00"), comment="单次冲压费用比例")

    # 扩展信息
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 关联
    part: Mapped["StampingPart"] = relationship("StampingPart", back_populates="processes")

    __table_args__ = (
        Index("ix_process_part_id", "part_id"),
        Index("ix_process_seq", "process_seq"),
    )
