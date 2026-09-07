"""基地主数据：规范名 + 别名附属行。"""

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class Location(AuditUserMixin, Base):
    """采购基地。主键即规范名；禁止 relationship 指向项目。"""

    __tablename__ = "locations"

    location: Mapped[str] = mapped_column(
        String(50), primary_key=True, comment="规范名，创建后只读"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="启用状态"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="下拉与列表顺序")
    aliases: Mapped[list["LocationAlias"]] = relationship(
        "LocationAlias",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class LocationAlias(Base):
    """基地别名。删基地时 CASCADE，不是独立主数据。"""

    __tablename__ = "location_aliases"

    alias: Mapped[str] = mapped_column(String(50), primary_key=True, comment="别名，全局唯一")
    location: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("locations.location", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="所属基地规范名",
    )
