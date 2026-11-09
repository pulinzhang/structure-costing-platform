"""费用档案：费用种类和全库统一的计费率。"""

from decimal import Decimal

from sqlalchemy import Boolean, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class FeeArchive(AuditUserMixin, Base):
    """费用档案。关联只用 id。不 relationship 计费行。"""

    __tablename__ = "fee_archives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="稳定键，创建后不改")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="页面主字")
    charge_basis: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="口径：amount 金额，rate 比例"
    )
    charge_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), nullable=False, comment="计费率，小数，0.02 表示 2%"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="列表顺序")
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="启用；停用后不能再被新计费选用"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    __table_args__ = (
        UniqueConstraint("code", name="uix_fee_archive_code"),
        UniqueConstraint("name", name="uix_fee_archive_name"),
        Index("ix_fee_archive_sort", "sort_order"),
        Index("ix_fee_archive_enabled", "is_enabled"),
    )
