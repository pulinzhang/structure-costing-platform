"""挡住删除的外键，对应一句处理建议。中文名在 schema_comment。"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RefHint(Base):
    """一条 (父表, 子表) 一句建议。"""

    __tablename__ = "ref_hint"

    parent_table: Mapped[str] = mapped_column(String(80), primary_key=True, comment="父表物理名")
    child_table: Mapped[str] = mapped_column(String(80), primary_key=True, comment="子表物理名")
    hint: Mapped[str] = mapped_column(String(200), nullable=False, comment="处理建议")
