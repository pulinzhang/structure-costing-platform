"""材料变更切点 — engineering_change_material_orders。"""

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class EngineeringChangeMaterialOrder(AuditUserMixin, Base):
    """Excel 一行 = 一刀。不落失效列。"""

    __tablename__ = "engineering_change_material_orders"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    upload_log_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "engineering_change_material_upload_logs.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
        index=True,
        comment="上传头",
    )
    upload_file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("upload_files.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="同头上存档",
    )
    change_version: Mapped[str] = mapped_column(String(20), nullable=False, comment="MAT-YYYYMM")
    excel_row: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Excel 行号；改图抄来的为空"
    )
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="基地")
    stamping_supplier: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("suppliers.full_name", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        comment="冲压工厂",
    )
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目")
    effective_year: Mapped[int] = mapped_column(Integer, nullable=False, comment="切点开始年")
    effective_month: Mapped[int] = mapped_column(Integer, nullable=False, comment="切点开始月")
    part_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="零件号")
    before_material: Mapped[str] = mapped_column(
        String(50),
        ForeignKey(
            "steel_grade_categories.grade",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
        comment="变更前材料",
    )
    after_material: Mapped[str] = mapped_column(
        String(50),
        ForeignKey(
            "steel_grade_categories.grade",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
        comment="变更后材料",
    )
    before_thickness: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, comment="变更前料厚"
    )
    after_thickness: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, comment="变更后料厚"
    )
    interchangeability: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="不影响互换性"
    )
    part_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="零件名称")
    source_part_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stamping_parts.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="工艺行 id",
    )
    copied_from_order_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "engineering_change_material_orders.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=True,
        comment="改图抄自旧号切点；Excel 上传为空",
    )

    __table_args__ = (
        UniqueConstraint(
            "location",
            "stamping_supplier",
            "vehicle_model",
            "part_number",
            "effective_year",
            "effective_month",
            name="uix_ecm_order_identity_month",
        ),
    )
