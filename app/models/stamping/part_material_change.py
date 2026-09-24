"""冲压零件材料变更历史。与工序同级，只挂零件主表。"""

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class StampingPartMaterialChange(AuditUserMixin, Base):
    """一刀材料变更。不落失效列，有效止由下一刀推出。"""

    __tablename__ = "stamping_part_material_changes"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    part_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stamping_parts.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="零件",
    )
    effective_year: Mapped[int] = mapped_column(Integer, nullable=False, comment="生效年")
    effective_month: Mapped[int] = mapped_column(Integer, nullable=False, comment="生效月")
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

    __table_args__ = (
        UniqueConstraint(
            "part_id",
            "effective_year",
            "effective_month",
            name="uix_part_material_change_month",
        ),
    )
