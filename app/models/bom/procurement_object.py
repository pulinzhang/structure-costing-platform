"""采购对象列表数据模型。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
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


class BomProcurementObjectList(AuditUserMixin, Base):
    """一版材料清单对应的一份采购对象列表头。"""

    __tablename__ = "bom_procurement_object_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    snapshot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bom_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="材料清单版本（删 snapshot 级联删清单）",
    )
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目/车型")
    bom_version: Mapped[str] = mapped_column(String(20), nullable=False, comment="材料清单版本")
    source_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="原始 Excel 文件名"
    )

    qa_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qa_error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    l0_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    l0_with_children_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    l2_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subassembly_child_sum: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    object_l0_degenerate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    object_l1_subassembly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    object_l1_stamping_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    other_leaf_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    anomaly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    generated_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    objects: Mapped[list["BomProcurementObject"]] = relationship(
        "BomProcurementObject",
        back_populates="object_list",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_bom_proc_obj_lists_scope", "location", "vehicle_model", "bom_version"),
    )


class BomProcurementObject(AuditUserMixin, Base):
    """采购对象列表行。"""

    __tablename__ = "bom_procurement_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    list_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bom_procurement_object_lists.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属采购对象列表",
    )
    section: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="object / other_leaf / anomaly"
    )
    object_kind: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="l0_degenerate / l1_subassembly / l1_stamping",
    )
    degenerate_subtype: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_node_id: Mapped[int] = mapped_column(Integer, nullable=False)

    part_number: Mapped[str] = mapped_column(String(50), nullable=False)
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    internal_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="内部号（从材料清单节点抄来；业务上当 ERP 编号联查）",
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    node_role: Mapped[str] = mapped_column(String(20), nullable=False)
    qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    qty_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="pcs")

    l0_part_number: Mapped[str] = mapped_column(String(50), nullable=False)
    l0_part_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parent_part_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parent_part_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    excel_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    excel_sheet_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    excel_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    child_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    weld_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_outsource_remark: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    material: Mapped[str | None] = mapped_column(String(50), nullable=True)
    thickness_text: Mapped[str | None] = mapped_column(String(50), nullable=True)
    material_mill: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey("suppliers.full_name", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=True,
        comment="合同对方规范全称；未指定为 NULL，禁止空串",
    )
    data_gap: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alert_code: Mapped[str | None] = mapped_column(String(200), nullable=True)

    confirm_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="pending / outsourced / in_house"
    )
    confirmed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirm_remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    audit_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="pending / approved"
    )
    audited_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    reverse_audited_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reverse_audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reverse_audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    object_list: Mapped[BomProcurementObjectList] = relationship(
        "BomProcurementObjectList",
        back_populates="objects",
    )

    __table_args__ = (
        UniqueConstraint("list_id", "source_node_id", name="uix_bom_proc_obj_list_node"),
        Index("ix_bom_proc_obj_section", "list_id", "section"),
        Index("ix_bom_proc_obj_audit", "list_id", "audit_status"),
        Index("ix_bom_proc_obj_part", "part_number"),
        Index("ix_bom_proc_obj_supplier", "supplier_name"),
    )
