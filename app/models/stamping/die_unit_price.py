"""冲压模具单价档案（核价政策，不算年度模具费）。"""

from decimal import Decimal

from sqlalchemy import ForeignKeyConstraint, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin

STATUS_EFFECTIVE = "effective"
STATUS_INVALID = "invalid"


class StampingDieUnitPrice(AuditUserMixin, Base):
    """模具单价档案。唯一键：基地 + 项目。"""

    __tablename__ = "stamping_die_unit_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目")
    steel_plate_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, comment="钢板模单价（万元/吨）"
    )
    progressive_die_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, comment="级进模单价（万元/吨）"
    )
    allocation_qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("10"), comment="项目分摊数量（万台）"
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
            name="uix_die_unit_price_location_vehicle",
        ),
        Index("ix_die_unit_price_vehicle", "vehicle_model"),
        Index("ix_die_unit_price_status", "status"),
        ForeignKeyConstraint(
            ["location", "vehicle_model"],
            ["vehicle_models.location", "vehicle_models.vehicle_model"],
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            name="fk_stamping_die_unit_prices_vehicle_models",
        ),
    )
