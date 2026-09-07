"""冲压检具费档案（按零件，不算年度分摊）。"""

from decimal import Decimal

from sqlalchemy import ForeignKeyConstraint, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin

STATUS_EFFECTIVE = "effective"
STATUS_INVALID = "invalid"
DEFAULT_GAUGE_FEE = Decimal("0.8")
DEFAULT_ALLOCATION_QTY = Decimal("10")


class StampingGaugeFee(AuditUserMixin, Base):
    """检具费档案。唯一键：基地 + 项目 + 零件号。"""

    __tablename__ = "stamping_gauge_fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目")
    part_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="零件号")
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="零件名称")
    gauge_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, comment="检具费（万元）"
    )
    allocation_qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=DEFAULT_ALLOCATION_QTY,
        comment="项目分摊数量（万台）",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=STATUS_EFFECTIVE,
        comment="effective=生效，invalid=失效",
    )

    __table_args__ = (
        UniqueConstraint(
            "location",
            "vehicle_model",
            "part_number",
            name="uix_gauge_fee_location_vehicle_part",
        ),
        Index("ix_gauge_fee_vehicle", "vehicle_model"),
        Index("ix_gauge_fee_part_number", "part_number"),
        Index("ix_gauge_fee_status", "status"),
        ForeignKeyConstraint(
            ["location", "vehicle_model"],
            ["vehicle_models.location", "vehicle_models.vehicle_model"],
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            name="fk_stamping_gauge_fees_vehicle_models",
        ),
    )
