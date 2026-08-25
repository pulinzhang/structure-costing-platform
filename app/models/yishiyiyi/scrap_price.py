"""
冲压废料月度销售价格数据模型
"""

from decimal import Decimal

from sqlalchemy import Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class StampingScrapPrice(AuditUserMixin, Base):
    """
    冲压废料月度销售价格表

    业务语义：
    - market_price：大盘价（含杂费的账面价，参考外部基准价）
    - deduction_fee：扣费（运费/扣水/扣杂/打包费等，无则填 0）
    - net_price：净价 = market_price - deduction_fee（由 Service 写入并持久化）

    唯一约束：同一基地/物料 + 年 + 月不可重复。
    """

    __tablename__ = "stamping_scrap_prices"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )

    # 【维度】
    location: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="基地/物料名称，例：芜湖、大连、青岛、福州、鄂尔多斯、铝板",
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="年份，例：2025")
    month: Mapped[int] = mapped_column(Integer, nullable=False, comment="月份（1-12）")

    # 【核心价格】
    market_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="大盘价（元/吨，含杂费的账面价）",
    )
    deduction_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="扣费（元/吨，运费/扣水/扣杂/打包费等，无则 0）",
    )
    net_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="净价（元/吨）= 大盘价 - 扣费，由业务层写入",
    )

    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注说明")

    __table_args__ = (
        UniqueConstraint(
            "location",
            "year",
            "month",
            name="uix_scrap_price_location_year_month",
        ),
        Index("ix_scrap_price_year", "year"),
        Index("ix_scrap_price_month", "month"),
        Index("ix_scrap_price_location", "location"),
        Index("ix_scrap_price_lookup", "year", "month", "location"),
    )
