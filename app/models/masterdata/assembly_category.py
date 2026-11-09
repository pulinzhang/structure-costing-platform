"""总成分类：冲压件、凸焊件、总成件、黑漆件。"""

from sqlalchemy import Boolean, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class AssemblyCategory(AuditUserMixin, Base):
    """总成分类。关联只用 id。不 relationship 计费行。"""

    __tablename__ = "assembly_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="稳定键，创建后不改")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="页面主字")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="列表顺序")
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="启用；停用后不能再被新计费选用"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    __table_args__ = (
        UniqueConstraint("code", name="uix_assembly_category_code"),
        UniqueConstraint("name", name="uix_assembly_category_name"),
        Index("ix_assembly_category_sort", "sort_order"),
        Index("ix_assembly_category_enabled", "is_enabled"),
    )
