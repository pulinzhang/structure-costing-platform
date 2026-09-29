"""
钢价政策数据模型
采用严格主子表架构：政策主表 + 阶梯明细表
"""

from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class SteelPricePolicy(AuditUserMixin, Base):
    """
    政策主表 - 统一的钢价政策头表
    一条政策对应多条阶梯明细
    """

    __tablename__ = "steel_price_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 生效周期
    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="生效年度（如：2026）")
    month: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="生效月份（1-12，如：4 表示 4 月）"
    )

    # 钢厂与钢种
    steel_mill: Mapped[str] = mapped_column(String(100), nullable=False, comment="钢厂全称，对表头")
    steel_mill_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("steel_mills.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        comment="钢厂档案 id",
    )
    category_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="钢种大类（如：'冷轧钢'、'镀锌钢'）"
    )

    # 政策类型与条件
    policy_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="政策类型：THICKNESS=厚度加减价，WIDTH=宽度加价"
    )
    # grade_type: GRADE=钢种牌号（如 DC01），WIDTH_RANGE=宽度范围（如 700≤W<900），CATEGORY=钢材类别（如 冷轧钢）
    grade_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="grade_value 的语义类型：GRADE/WIDTH_RANGE/CATEGORY"
    )
    grade_value: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="牌号或宽度范围（GRADE 时如 'DC01'，WIDTH_RANGE 时如 '700≤W<900'，CATEGORY 时如 '冷轧钢'）",
    )
    base_thickness: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="基准厚度（仅厚度政策需要，如 1.00）"
    )

    # 元数据
    excel_filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="来源 Excel 文件名"
    )

    # 关联子表（cascade 确保删除主表时自动删除所有明细）
    items: Mapped[list["SteelPriceLadderItem"]] = relationship(
        "SteelPriceLadderItem",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="SteelPriceLadderItem.sort_order, SteelPriceLadderItem.id",
    )

    __table_args__ = (
        Index("ix_policy_year", "year"),
        Index("ix_policy_month", "month"),
        Index("ix_policy_steel_mill", "steel_mill"),
        Index("ix_policy_steel_mill_id", "steel_mill_id"),
        Index("ix_policy_category_name", "category_name"),
        Index("ix_policy_policy_type", "policy_type"),
        Index("ix_policy_grade_type", "grade_type"),
        Index("ix_policy_grade_value", "grade_value"),
        Index("ix_policy_base_thickness", "base_thickness"),
        # 业务唯一约束：同年度、月份、钢厂、大类、类型、牌号、基准厚度唯一
        UniqueConstraint(
            "year",
            "month",
            "steel_mill_id",
            "category_name",
            "policy_type",
            "grade_value",
            "base_thickness",
            name="uix_policy_business_key",
        ),
    )


class SteelPriceLadderItem(AuditUserMixin, Base):
    """
    阶梯明细表 - 采用 min/max 区间设计的加减价阶梯
    """

    __tablename__ = "steel_price_ladder_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("steel_price_policies.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属政策 ID",
    )

    # 附加子分组（如镀锌宽度加价中的 "厚度≤1.5mm" 或冷轧宽度中的 "DC01、DC03"）
    target_sub_group: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="附加子分组条件"
    )

    # 厚度区间
    thick_min: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True, comment="厚度下限值（mm）"
    )
    thick_min_operator: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="厚度下限操作符（如 '>=' 或 '>'）"
    )
    thick_max: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True, comment="厚度上限值（mm）"
    )
    thick_max_operator: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="厚度上限操作符（如 '<=' 或 '<'）"
    )

    # 宽度区间
    width_min: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True, comment="宽度下限值（mm）"
    )
    width_min_operator: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="宽度下限操作符（如 '>=' 或 '>'）"
    )
    width_max: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True, comment="宽度上限值（mm）"
    )
    width_max_operator: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="宽度上限操作符（如 '<=' 或 '<'）"
    )

    # 锌层克重区间（g/m²）
    zinc_coating_min: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True, comment="锌层克重下限值（g/m²）"
    )
    zinc_coating_min_operator: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="锌层克重下限操作符（如 '>=' 或 '>'）"
    )
    zinc_coating_max: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 2), nullable=True, comment="锌层克重上限值（g/m²）"
    )
    zinc_coating_max_operator: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="锌层克重上限操作符（如 '<=' 或 '<'）"
    )

    # 对应的加减价金额（元/吨，整数精确到元）
    price_adjustment: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="加减价金额（元/吨）"
    )

    # Excel 原始位置（用于测试核对）
    excel_row: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Excel 行号（1-based）"
    )
    excel_col: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Excel 列号（1-based）"
    )

    # 是否为基准厚度（加价为0）
    is_base: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="是否为基准厚度：0=否，1=是"
    )

    # 匹配排序号
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="匹配排序号"
    )

    # 关联主表
    policy: Mapped["SteelPricePolicy"] = relationship("SteelPricePolicy", back_populates="items")

    __table_args__ = (
        Index("ix_ladder_policy_id", "policy_id"),
        Index("ix_ladder_thick_min", "thick_min"),
        Index("ix_ladder_thick_max", "thick_max"),
        Index("ix_ladder_width_min", "width_min"),
        Index("ix_ladder_width_max", "width_max"),
        Index("ix_ladder_zinc_coating_min", "zinc_coating_min"),
        Index("ix_ladder_zinc_coating_max", "zinc_coating_max"),
        Index("ix_ladder_sort_order", "sort_order"),
    )
