"""钢材价格数据模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint

from app.database import Base


class SteelPrice(Base):
    """按年度、月份、牌号、厚度作为业务主键的钢材吨价。"""

    __tablename__ = "steel_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, comment="年度")
    month = Column(Integer, nullable=False, comment="月份")
    steel_type = Column(String(50), nullable=False, comment="钢种")
    grade = Column(String(100), nullable=False, comment="牌号")
    reference_spec = Column(String(100), nullable=False, comment="参考规格")
    steel_mill = Column(String(100), nullable=False, comment="钢厂")
    bid_price = Column(Numeric(14, 4), nullable=False, comment="中标价")
    thickness = Column(Numeric(10, 4), nullable=False, comment="厚度")
    thickness_adjustment = Column(Numeric(14, 4), nullable=False, comment="厚度加减价")
    processing_fee = Column(Numeric(14, 4), nullable=False, comment="加工费")
    final_price_per_ton = Column(Numeric(14, 4), nullable=False, comment="最终价/吨")
    remark = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
        comment="更新时间",
    )

    __table_args__ = (
        Index("ix_steel_price_year_month", "year", "month"),
        Index("ix_steel_price_grade", "grade"),
        Index("ix_steel_price_steel_type", "steel_type"),
        UniqueConstraint(
            "year",
            "month",
            "grade",
            "thickness",
            name="uix_steel_price_business_key",
        ),
    )
