"""
冲压零件价格核算结果表

原材料净成本对齐工艺清单 R 列，三项严格分列存储：
  R = M×P×(1+λ) − M×λ×η×Q − O×η×Q
  ① material_amount_sheet      = M×P×(1+λ)     钢材采购
  ② loss_scrap_deduction      = M×λ×η×Q       损耗废料扣除
  ③ process_scrap_deduction   = O×η×Q         边角废料扣除
  scrap_amount_sheet = ②+③（合计，便于兼容）
  material_net_per_part = ①−②−③
  ρ_steel / λ / η 来自系统配置快照（默认 7.85 / 0.003 / 0.97）。
"""

from decimal import Decimal
from datetime import datetime
from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class StampingPartCost(AuditUserMixin, Base):
    """冲压零件价格核算结果"""

    __tablename__ = "stamping_part_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="计算年度")
    month: Mapped[int] = mapped_column(Integer, nullable=False, comment="计算月份")
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    stamping_supplier: Mapped[str] = mapped_column(String(50), nullable=False, comment="冲压工厂")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="车型")
    version: Mapped[str] = mapped_column(String(20), nullable=False, comment="版本")

    # —— 零件主表快照 ——
    source_part_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="来源零件主表 id"
    )
    seq_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="序号")
    part_number: Mapped[str] = mapped_column(String(50), nullable=False, comment="零件号")
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="零件名称")
    material: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="材质")
    thickness: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True, comment="料厚(mm)"
    )
    part_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="零件重量(kg)"
    )
    sheet_length: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="料片长/卷料宽(mm)"
    )
    sheet_width: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="料片宽/卷料步距(mm)"
    )
    parts_per_sheet: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="可制件数")
    sheet_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="料片式样")
    die_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="模具类型")
    process_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="工艺方法"
    )
    automation: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="自动化原文快照"
    )
    part_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="零件备注快照")
    sketch_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="零件简图URL"
    )
    excel_filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="来源Excel文件名"
    )
    excel_sheet_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="来源工作表名"
    )
    excel_row: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="来源Excel行号")
    excel_part_col: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="零件号所在列号"
    )

    # —— 过程量（奇瑞口径）——
    density: Mapped[Decimal] = mapped_column(
        Numeric(6, 4),
        nullable=False,
        default=Decimal("7.85"),
        comment="密度(g/cm3)，来自系统配置快照",
    )
    material_loss_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=Decimal("0.003"),
        comment="材料损耗率（小数），来自系统配置快照",
    )
    scrap_recovery_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=Decimal("0.97"),
        comment="废料回收率（小数），来自系统配置快照",
    )
    blank_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 10),
        nullable=True,
        comment="预估单件材料消耗M(kg)=L×W×T×密度/1e6/可制件数",
    )
    finished_total_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 10),
        nullable=True,
        comment="成品净重H(kg)，对齐 Excel 净重",
    )
    scrap_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 10),
        nullable=True,
        comment="废料重量O(kg)=M−H",
    )
    material_utilization_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True, comment="材料利用率(%)"
    )

    # —— 取价溯源 ——
    steel_price_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="钢材联动价 id"
    )
    steel_mill: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="中标钢厂")
    steel_ton_price: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True, comment="钢材一事一议吨价(元/吨)"
    )
    scrap_price_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="废料月度价 id"
    )
    scrap_ton_price: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True, comment="废料净价(元/吨)"
    )
    process_fee_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="加工费结果 id"
    )
    process_fee_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True, comment="加工费(元/件)"
    )

    # —— 金额（对齐 Excel R：①−②−③）——
    material_amount_sheet: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="①钢材采购=M×P×(1+λ)（单件，元；P=元/kg=吨价/1000）",
    )
    loss_scrap_deduction: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="②损耗废料扣除=M×λ×η×Q（单件，元）",
    )
    process_scrap_deduction: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="③边角废料扣除=O×η×Q（单件，元）",
    )
    scrap_amount_sheet: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="废料扣除合计=②+③（单件，元）",
    )
    material_net_per_part: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="原材料成本R（单件，元）=①−②−③",
    )
    direct_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="直接成本=R(元)+加工费(元)",
    )
    finished_finance_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="成品财务费=直接成本×财务费率（元）",
    )
    finished_management_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="成品管理费=直接成本×管理费率（元）",
    )
    finished_warehouse_packaging_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="仓储+包装管理费用=直接成本×仓储+包装管理费用率（元）",
    )
    finished_pretax_profit_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="成品税前利润=直接成本×税前利润率（元）",
    )

    unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6),
        nullable=True,
        comment="单件成本=直接成本+成品财务费+成品管理费+仓储+包装管理费用+成品税前利润(元)",
    )

    # —— 批次 / 状态 ——
    calc_batch_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="计算批次号"
    )
    calc_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        comment="单件计算状态：success / failed",
    )
    calc_fail_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="计算失败原因"
    )
    formula_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="公式版本，如 part-cost-v6"
    )
    calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="计算时间"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    audit_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="审核状态：pending / approved / rejected",
    )
    audited_by: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="审核人")
    audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审核时间")
    audit_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核意见")
    reverse_audited_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="反审核人"
    )
    reverse_audited_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="反审核时间"
    )
    reverse_audit_remark: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="反审核原因"
    )

    __table_args__ = (
        Index("ix_stamping_part_cost_year_month", "year", "month"),
        Index("ix_stamping_part_cost_location", "location"),
        Index("ix_stamping_part_cost_supplier", "stamping_supplier"),
        Index("ix_stamping_part_cost_part_number", "part_number"),
        Index("ix_stamping_part_cost_audit_status", "audit_status"),
        Index("ix_stamping_part_cost_calc_batch", "calc_batch_id"),
        UniqueConstraint(
            "year",
            "month",
            "location",
            "stamping_supplier",
            "vehicle_model",
            "version",
            "part_number",
            name="uix_stamping_part_cost_unique_key",
        ),
    )
