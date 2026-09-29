"""系统配置（单例行）。"""

from decimal import Decimal

from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.system_defaults import (
    DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT,
    DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT,
    DEFAULT_BODY_PANEL_MAX_THICKNESS,
    DEFAULT_FINISHED_FINANCE_RATE,
    DEFAULT_FINISHED_MANAGEMENT_RATE,
    DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
    DEFAULT_FINISHED_SCRAP_RATE,
    DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE,
    DEFAULT_MATERIAL_LOSS_RATE,
    DEFAULT_SCRAP_RECOVERY_RATE,
    DEFAULT_STEEL_DENSITY,
    DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON,
)
from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class SystemConfig(AuditUserMixin, Base):
    """系统配置表（仅维护 id=1 单例行）"""

    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, comment="固定为 1"
    )
    app_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="应用名称")
    company_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
        comment="公司名称（采购协议甲方）",
    )
    procurement_agreement_remarks: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="采购价格协议文尾条款（占位符见设置页）",
    )
    steel_density: Mapped[Decimal] = mapped_column(
        Numeric(6, 4),
        nullable=False,
        default=DEFAULT_STEEL_DENSITY,
        comment="钢材密度(g/cm3)，默认 7.85",
    )
    material_loss_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=DEFAULT_MATERIAL_LOSS_RATE,
        comment="冲压材料损耗率（小数，默认 0.003=千分之3）",
    )
    scrap_recovery_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=DEFAULT_SCRAP_RECOVERY_RATE,
        comment="废料回收率（小数，默认 0.97=97%）",
    )
    finished_finance_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=DEFAULT_FINISHED_FINANCE_RATE,
        comment="成品财务费率（小数，默认 0.02=2%）",
    )
    finished_management_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=DEFAULT_FINISHED_MANAGEMENT_RATE,
        comment="成品管理费率（小数，默认 0.02=2%）",
    )
    finished_warehouse_packaging_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE,
        comment="仓储+包装管理费用率（小数，默认 0.01=1%）",
    )
    finished_scrap_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=DEFAULT_FINISHED_SCRAP_RATE,
        comment="成品报废率（小数，默认 0.003=千分之3）",
    )
    finished_pretax_profit_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
        comment="成品税前利润率（小数，默认 0.02=2%）",
    )
    swing_shear_process_fee_per_ton: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=DEFAULT_SWING_SHEAR_PROCESS_FEE_PER_TON,
        comment="摆剪件加到钢价上的金额（元/吨），默认 150",
    )
    base_price_month_move_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=DEFAULT_BASE_PRICE_MONTH_MOVE_LIMIT,
        comment="基准价月涨跌限额（元/吨）。同一基地同一规格，单价加加工费相对上月超过此值则整批拒绝。默认 300",
    )
    base_price_processing_fee_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=DEFAULT_BASE_PRICE_PROCESSING_FEE_LIMIT,
        comment="基准价加工费上限（元/吨）。大于此值整批拒绝，等于此值允许",
    )
    body_panel_max_thickness: Mapped[Decimal] = mapped_column(
        Numeric(7, 2),
        nullable=False,
        default=DEFAULT_BODY_PANEL_MAX_THICKNESS,
        comment="乘用车车身钢板冲压件料厚上限（mm）。参考规格厚度大于此值则整批拒绝。默认 3.00，等于此值允许",
    )
