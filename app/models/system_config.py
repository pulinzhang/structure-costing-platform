"""系统配置（单例行）。"""

from decimal import Decimal
from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.audit_mixin import AuditUserMixin

class SystemConfig(AuditUserMixin, Base):
    """系统配置表（仅维护 id=1 单例行）"""

    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, comment="固定为 1")
    app_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="应用名称")
    steel_density: Mapped[Decimal] = mapped_column(
        Numeric(6, 4),
        nullable=False,
        default=7.85,
        comment="钢材密度(g/cm3)，默认 7.85",
    )
    material_loss_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=0.003,
        comment="冲压材料损耗率（小数，默认 0.003=千分之3）",
    )
    scrap_recovery_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
        default=0.97,
        comment="废料回收率（小数，默认 0.97=97%）",
    )
