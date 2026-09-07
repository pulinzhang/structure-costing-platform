"""冲压模具布点主从表（模具费计算依据）。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    ForeignKeyConstraint,
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


class StampingDiePart(AuditUserMixin, Base):
    """模具零件主表。唯一键：基地 + 项目 + 零件号。"""

    __tablename__ = "stamping_die_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目")
    stamping_supplier: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="冲压供应商（布点阶段不填）"
    )
    version: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="版本（布点阶段不填）"
    )
    seq_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="序号")
    part_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="零件号")
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="零件名称")
    material: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="材质")
    thickness: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True, comment="料厚(mm)"
    )
    part_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="净重(kg)"
    )
    sheet_length: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="料片长(mm)"
    )
    sheet_width: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="料片宽(mm)"
    )
    sheet_shape: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="板料形状")
    parts_per_sheet: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="可制件数")
    material_consumption: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="预估单件材料消耗(kg)"
    )
    material_utilization: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True, comment="材料利用率(0-1)"
    )
    estimated_weight_subtotal_t: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="预估重量小计(T)"
    )
    die_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="模具类型")
    die_method: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="模具方式")
    production_mode: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="生产方式"
    )
    needs_end_effector: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="是否需要端拾器（原文）"
    )
    part_grade: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="零件等级")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    excel_filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="来源文件名")
    excel_sheet_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    excel_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    excel_part_col: Mapped[int | None] = mapped_column(Integer, nullable=True)

    processes: Mapped[list[StampingDieProcess]] = relationship(
        "StampingDieProcess",
        back_populates="part",
        cascade="all, delete-orphan",
        order_by="StampingDieProcess.process_order",
    )

    __table_args__ = (
        UniqueConstraint(
            "location",
            "vehicle_model",
            "part_number",
            name="uix_stamping_die_part_scope",
        ),
        Index("ix_die_part_location_vehicle", "location", "vehicle_model"),
        Index("ix_die_part_number", "part_number"),
        ForeignKeyConstraint(
            ["location", "vehicle_model"],
            ["vehicle_models.location", "vehicle_models.vehicle_model"],
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            name="fk_stamping_die_parts_vehicle_models",
        ),
    )


class StampingDieProcess(AuditUserMixin, Base):
    """模具工序子表。"""

    __tablename__ = "stamping_die_processes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    die_part_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stamping_die_parts.id", ondelete="CASCADE"),
        nullable=False,
    )
    process_seq: Mapped[str] = mapped_column(String(20), nullable=False, comment="工序序号")
    process_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    process_code: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="工序")
    die_sets: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="套数")
    die_number: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="模具编号（布点 Excel 或上传按规则生成）"
    )
    die_length: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="模具长"
    )
    die_width: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="模具宽"
    )
    die_height: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="模具高"
    )
    hollow_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True, comment="掏空系数"
    )
    estimated_weight_t: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="预估重量(T)"
    )
    tonnage: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="设备吨位")
    alloc_ratio: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("1.00"), comment="分摊比例"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    part: Mapped[StampingDiePart] = relationship("StampingDiePart", back_populates="processes")

    __table_args__ = (
        UniqueConstraint("die_part_id", "process_seq", name="uix_die_process_part_seq"),
        Index("ix_die_process_part_id", "die_part_id"),
    )
