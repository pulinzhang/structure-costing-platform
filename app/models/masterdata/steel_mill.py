"""钢厂主数据：缩写给人看，全称对表头，别名附属。"""

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class SteelMill(AuditUserMixin, Base):
    """钢厂。关联只用 id。头表不 relationship 别名。"""

    __tablename__ = "steel_mills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    abbreviation: Mapped[str] = mapped_column(String(50), nullable=False, comment="缩写，页面主字")
    full_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="全称，对 Excel 表头"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="启用；停用后不能再选用"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="列表顺序")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    __table_args__ = (
        UniqueConstraint("abbreviation", name="uix_steel_mill_abbreviation"),
        UniqueConstraint("full_name", name="uix_steel_mill_full_name"),
        Index("ix_steel_mill_enabled", "is_enabled"),
        Index("ix_steel_mill_sort", "sort_order"),
    )


class SteelMillAlias(Base):
    """钢厂别名。删钢厂时 CASCADE。"""

    __tablename__ = "steel_mill_aliases"

    alias: Mapped[str] = mapped_column(String(50), primary_key=True, comment="别名，全局唯一")
    steel_mill_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("steel_mills.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="所属钢厂",
    )
