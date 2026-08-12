"""
钢材基准价格数据模型
适配多基地、多年份宽表清洗入库
"""

from decimal import Decimal

from sqlalchemy import Column, Index, Integer, Numeric, String, Text, UniqueConstraint

from app.database import Base
from app.models.audit_mixin import AuditUserMixin


class SteelBasePrice(AuditUserMixin, Base):
    """
    钢材基准价格表（适配多基地、多年份宽表清洗入库）

    核心特点：
    - 纯粹基准价，不含人工临时下调
    - 防扯皮溯源铁证字段（excel_filename、sheet_name、excel_row）
    - 复合唯一约束确保同批次、同基地、同钢厂牌号、同规格不会重复写入
    """

    __tablename__ = "steel_base_prices"

    # 主键 ID
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 【时间维度：区隔发布时间与生效原料月份】
    year = Column(Integer, nullable=False, comment="订单发布年份，例：2024")
    month = Column(Integer, nullable=False, comment="订单发布月份，例：12")

    # 【基地与归属维度】
    location = Column(
        String(50), nullable=False, comment="采购基地，例：芜湖基地、大连基地、青岛基地、鄂尔多斯基地"
    )

    # 【钢厂与牌号维度】
    steel_mill = Column(
        String(50), nullable=False, comment="中标钢厂，例：VAMA、本钢、马钢、首钢、唐钢、山钢"
    )
    category_name = Column(String(50), nullable=False, comment="钢种大类，例：镀锌、冷轧、酸洗")
    grade = Column(String(50), nullable=False, comment="钢材牌号，例：DC51D+Z、DC01")
    #规格（厚度*宽度）
    spec = Column(String(50), nullable=False, comment="规格，例：1.00*1250.00")
    # 【基准规格维度】
    thick = Column(Numeric(7, 2), nullable=False, comment="参考厚度(mm)，例：1.00")
    width = Column(Numeric(7, 2), nullable=False, comment="参考宽度(mm)，例：1250.00")

    # 【核心价格要素（纯粹基准价，不含人工临时下调）】
    base_price = Column(Numeric(10, 2), nullable=False, comment="到厂原卷承兑价格(元/吨)")
    processing_fee = Column(
        Numeric(10, 2), nullable=False, default=Decimal("120.00"), comment="原卷加工费(元/吨)"
    )

    # 【防扯皮与溯源铁证字段（核心亮点）】
    excel_filename = Column(
        String(255),
        nullable=False,
        comment="来源Excel文件名，例：外协钢板2024年12月订单.xlsx",
    )
    sheet_name = Column(String(100), nullable=False, comment="Excel表页名称，例：定价表")
    excel_row = Column(Integer, nullable=False, comment="源数据在Excel中的具体行号，对应序号列，例：1")
    excel_col = Column(Integer, nullable=True, comment="Excel 列号（1-based）")

    # 【辅助与扩展】
    remark = Column(Text, nullable=True, comment="备注说明")

    # 【复合唯一约束 + 高性能组合索引】
    __table_args__ = (
        # 确保同批次、同基地、同钢厂牌号、同规格不会重复写入
        UniqueConstraint(
            "year",
            "month",
            "location",
            "steel_mill",
            "category_name",
            "grade",
            "thick",
            "width",
            name="uix_base_price_business_key",
        ),
        # 高性能组合索引：供 Python 或 SQL 高手编写查价视图时毫秒级命中
        Index("ix_base_price_year", "year"),
        Index("ix_base_price_month", "month"),
        Index("ix_base_price_steel_mill", "steel_mill"),
        Index("ix_base_price_category_name", "category_name"),
        Index("ix_base_price_grade", "grade"),
        Index("ix_base_price_lookup", "year", "month", "location", "category_name", "grade"),
    )
