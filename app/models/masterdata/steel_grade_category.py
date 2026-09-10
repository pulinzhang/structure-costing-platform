"""牌号分类档案：一个 grade 一行，挂冷轧 / 镀锌 / 酸洗。"""

from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class SteelGradeCategory(AuditUserMixin, Base):
    """
    牌号分类档案。

    唯一键只有 grade；category_name / category_seq 是必填属性。
    """

    __tablename__ = "steel_grade_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="大类：冷轧 / 镀锌 / 酸洗",
    )
    category_seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="展示序号，由大类派生：冷轧=1、镀锌=2、酸洗=3",
    )
    grade: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="钢材牌号，与基价 grade、零件 material 对齐"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    __table_args__ = (
        UniqueConstraint("grade", name="uix_steel_grade_category_grade"),
        Index("ix_steel_grade_category_name", "category_name"),
        Index("ix_steel_grade_category_seq", "category_seq"),
    )
