"""钢材价格计算结果数据模型。"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import (

    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.audit_mixin import AuditUserMixin


class SteelPrice(AuditUserMixin, Base):
    """
    钢材价格计算结果表

    计算链：
      stamping 材质需求
        → steel_base_prices 基准价
        → steel_price_policies / ladder_items 加减价
        → 本表落库

    业务唯一键：
      year + month + location + steel_mill + category_name
      + grade + thickness + width

    公式：
      final_price_per_ton
        = base_price
        + thickness_adjustment
        + width_adjustment
        + zinc_adjustment
        + processing_fee
        + other_adjustment

    审核锁定：
      audit_status == 'approved' 时，禁止删除、修改、重算覆盖；
      须先反审核为 pending。
    """

    __tablename__ = "steel_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键 ID")

    # 一、时间与匹配维度（业务主键）
    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="订单/生效年份，例：2025")
    month: Mapped[int] = mapped_column(Integer, nullable=False, comment="订单/生效月份，例：11")
    location: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="采购基地，例：芜湖基地、大连基地、青岛基地、鄂尔多斯基地",
    )
    steel_mill: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="中标钢厂，例：马钢、首钢、唐钢、VAMA",
    )
    category_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="钢种大类，例：镀锌、冷轧、酸洗",
    )
    grade: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="钢材牌号，例：DC01、DC51D+Z",
    )
    thickness: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, comment="实际料厚(mm)")
    width: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="实际宽度(mm)，用于宽度加减价匹配",
    )
    spec: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="展示用规格，例：1.00*1250.00")

    # 二、价格分项
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        comment="基准到厂价(元/吨)，来自 steel_base_prices.base_price",
    )
    thickness_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0"),
        comment="厚度加减价(元/吨)",
    )
    width_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0"),
        comment="宽度加减价(元/吨)",
    )
    zinc_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0"),
        comment="锌层加减价(元/吨)，无则 0",
    )
    processing_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0"),
        comment="原卷加工费(元/吨)",
    )
    other_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0"),
        comment="其他/人工临时调整(元/吨)，默认 0",
    )
    final_price_per_ton: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        comment="最终吨价(元/吨) = 上述分项之和",
    )

    # 三、溯源 FK + Excel 四件套
    base_price_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("steel_base_prices.id", ondelete="SET NULL"),
        nullable=True,
        comment="命中的基准价记录 ID",
    )
    base_excel_filename: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="基准价来源 Excel 文件名")
    base_sheet_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="基准价来源 Excel 表页名")
    base_excel_row: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="基准价来源 Excel 行号（1-based）")
    base_excel_col: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="基准价来源 Excel 列号（1-based）")

    thickness_policy_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("steel_price_policies.id", ondelete="SET NULL"),
        nullable=True,
        comment="命中的厚度政策头 ID",
    )
    thickness_ladder_item_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("steel_price_ladder_items.id", ondelete="SET NULL"),
        nullable=True,
        comment="命中的厚度阶梯明细 ID",
    )
    thickness_excel_filename: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="厚度政策来源 Excel 文件名")
    thickness_sheet_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="厚度政策来源 Excel 表页名")
    thickness_excel_row: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="厚度加减价来源 Excel 行号（1-based）")
    thickness_excel_col: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="厚度加减价来源 Excel 列号（1-based）")

    width_policy_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("steel_price_policies.id", ondelete="SET NULL"),
        nullable=True,
        comment="命中的宽度政策头 ID",
    )
    width_ladder_item_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("steel_price_ladder_items.id", ondelete="SET NULL"),
        nullable=True,
        comment="命中的宽度阶梯明细 ID",
    )
    width_excel_filename: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="宽度政策来源 Excel 文件名")
    width_sheet_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="宽度政策来源 Excel 表页名")
    width_excel_row: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="宽度加减价来源 Excel 行号（1-based）")
    width_excel_col: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="宽度加减价来源 Excel 列号（1-based）")

    zinc_policy_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("steel_price_policies.id", ondelete="SET NULL"),
        nullable=True,
        comment="命中的锌层政策头 ID",
    )
    zinc_ladder_item_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("steel_price_ladder_items.id", ondelete="SET NULL"),
        nullable=True,
        comment="命中的锌层阶梯明细 ID",
    )
    zinc_excel_filename: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="锌层政策来源 Excel 文件名")
    zinc_sheet_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="锌层政策来源 Excel 表页名")
    zinc_excel_row: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="锌层加减价来源 Excel 行号（1-based）")
    zinc_excel_col: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="锌层加减价来源 Excel 列号（1-based）")

    # 四、计算元数据
    calc_batch_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="计算批次号（同一次重算共用）")
    match_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment=(
            "匹配状态：full_match / base_only / no_base / "
            "no_thickness_policy / no_width_policy / partial / failed / manual"
        ),
    )
    calc_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        comment="计算状态：success / partial / failed",
    )
    calc_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="匹配失败或部分匹配原因")
    formula_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="v1",
        comment="计价公式版本",
    )
    calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="本次计算完成时间")

    # 五、审核锁定 + 反审核留痕
    audit_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="审核状态：pending=待审，approved=已通过，rejected=已驳回",
    )
    audited_by: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最近一次审核人（经理）")
    audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近一次审核时间")
    audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近一次审核意见（通过/驳回）")
    reverse_audited_by: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="反审核人（经理）")
    reverse_audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="反审核时间")
    reverse_audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="反审核原因")

    # 六、辅助与审计
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="人工备注（不承担溯源）")

    __table_args__ = (
        UniqueConstraint(
            "year",
            "month",
            "location",
            "steel_mill",
            "category_name",
            "grade",
            "thickness",
            "width",
            name="uix_steel_price_business_key",
        ),
        Index("ix_steel_price_year_month", "year", "month"),
        Index("ix_steel_price_location", "location"),
        Index("ix_steel_price_steel_mill", "steel_mill"),
        Index("ix_steel_price_category_name", "category_name"),
        Index("ix_steel_price_grade", "grade"),
        Index("ix_steel_price_calc_batch_id", "calc_batch_id"),
        Index("ix_steel_price_match_status", "match_status"),
        Index("ix_steel_price_audit_status", "audit_status"),
        Index("ix_steel_price_base_price_id", "base_price_id"),
        Index(
            "ix_steel_price_lookup",
            "year",
            "month",
            "location",
            "category_name",
            "grade",
        ),
    )
