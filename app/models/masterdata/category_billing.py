"""计费管理：一个总成分类选用一条费用档案。"""

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin
from app.models.masterdata.assembly_category import AssemblyCategory
from app.models.masterdata.fee_archive import FeeArchive


class AssemblyCategoryBilling(AuditUserMixin, Base):
    """分类与费用的对照。勾选即有行，取消即删除。两条外键都 RESTRICT。"""

    __tablename__ = "assembly_category_billings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assembly_category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assembly_categories.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        comment="总成分类",
    )
    fee_archive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fee_archives.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        comment="费用档案",
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    category: Mapped[AssemblyCategory] = relationship(
        foreign_keys="AssemblyCategoryBilling.assembly_category_id",
    )
    fee: Mapped[FeeArchive] = relationship(
        foreign_keys="AssemblyCategoryBilling.fee_archive_id",
    )

    __table_args__ = (
        UniqueConstraint(
            "assembly_category_id",
            "fee_archive_id",
            name="uix_assembly_category_billing_pair",
        ),
        Index("ix_assembly_category_billing_category", "assembly_category_id"),
        Index("ix_assembly_category_billing_fee", "fee_archive_id"),
    )
