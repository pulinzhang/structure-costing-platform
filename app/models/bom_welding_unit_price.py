"""
焊接单价数据模型
用于存储不同基地、不同年份的焊接/铆接等操作的单位工费单价
"""

from decimal import Decimal

from sqlalchemy import Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.audit_mixin import AuditUserMixin


class BomWeldingUnitPrice(AuditUserMixin, Base):
    """焊接单价表（按操作项目计的单位价格）"""

    __tablename__ = "bom_welding_unit_price"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    location: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="采购基地，例：青岛、芜湖、大连、鄂尔多斯",
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="年份（如 2026）")

    item_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="操作项目名称，例：焊点、CO2焊缝",
    )

    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="计量单位，例：个、CM、MM、平方",
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="工费单价(元/单位)，Numeric(12,4) 固定4位小数",
    )

    remark: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="备注",
    )

    __table_args__ = (
        Index("ix_welding_unit_price_location", "location"),
        Index("ix_welding_unit_price_year", "year"),
        Index("ix_welding_unit_price_item_name", "item_name"),
        UniqueConstraint(
            "location",
            "year",
            "item_name",
            name="uix_welding_unit_price_location_year_item",
        ),
    )
