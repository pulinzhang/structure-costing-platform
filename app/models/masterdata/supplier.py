"""供应商主数据：全称主键 + 别名附属行。"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class Supplier(AuditUserMixin, Base):
    """供应商。主键即规范全称；禁止 relationship 指向冲压 / BOM。"""

    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("abbreviation", name="uq_suppliers_abbreviation"),
        UniqueConstraint("erp_code", name="uq_suppliers_erp_code"),
    )

    full_name: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="全称，规范名；可改，RESTRICT 拦直接下一跳"
    )
    abbreviation: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="缩写，界面短名；可改"
    )
    erp_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="ERP 代码，对外身份；可改"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="启用状态"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="下拉与列表顺序")
    aliases: Mapped[list["SupplierAlias"]] = relationship(
        "SupplierAlias",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SupplierAlias(Base):
    """供应商别名。删供应商时 CASCADE，不是独立主数据。"""

    __tablename__ = "supplier_aliases"

    alias: Mapped[str] = mapped_column(String(100), primary_key=True, comment="别名，全局唯一")
    full_name: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("suppliers.full_name", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="所属供应商规范全称",
    )
