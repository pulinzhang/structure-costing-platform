"""物理表的中文名。SQLite 没有表 COMMENT，用这张表代替。"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SchemaComment(Base):
    """一张物理表一行。"""

    __tablename__ = "schema_comment"

    table_name: Mapped[str] = mapped_column(String(80), primary_key=True, comment="物理表名")
    slice: Mapped[str] = mapped_column(String(40), nullable=False, comment="现网切片")
    name_zh: Mapped[str] = mapped_column(String(80), nullable=False, comment="中文名")
    name_en: Mapped[str] = mapped_column(String(120), nullable=False, comment="英文说明")
