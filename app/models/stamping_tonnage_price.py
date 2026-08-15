"""
冲压冲次单价数据模型
用于存储不同基地、不同年份、不同压机吨位对应的单冲次加工价格
"""

from decimal import Decimal
from sqlalchemy import Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.audit_mixin import AuditUserMixin

class StampingTonnagePrice(AuditUserMixin, Base):
    """
    冲压冲次单价表
    用于存储不同基地、不同年份、不同压机吨位对应的单冲次加工价格
    """

    __tablename__ = "stamping_tonnage_price"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 采购基地（不同基地单价可能不同）
    location: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="采购基地，例：青岛、芜湖、大连、鄂尔多斯",
    )

    # 年份（用于区分不同年度的价格标准）
    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="年份（如 2026）")

    # 压机吨位（T）
    tonnage: Mapped[int] = mapped_column(Integer, nullable=False, comment="压机吨位(T)")

    # 单冲次价格（元/冲次），保留 3 位小数
    price_per_stroke: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, comment="单冲次价格(元)")

    __table_args__ = (
        Index("ix_tonnage_price_location", "location"),
        Index("ix_tonnage_price_year", "year"),
        Index("ix_tonnage_price_tonnage", "tonnage"),
        # 同基地同年份同吨位设为联合唯一约束
        UniqueConstraint(
            "location", "year", "tonnage",
            name="uix_location_year_tonnage_unique",
        ),
    )
