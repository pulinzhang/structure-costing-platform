"""工程变更效果链接 — engineering_change_effect_links（整本回滚用前后实体 id）。"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EngineeringChangeEffectLink(Base):
    """一次成功变更的前后实体 id；不存业务大字段。"""

    __tablename__ = "engineering_change_effect_links"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    upload_log_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("engineering_change_upload_logs.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="上传头（整本回滚）",
    )
    change_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("engineering_change_orders.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="变更单行",
    )
    effect_kind: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        comment="assembly_l0 / process_part / die_part / procurement_object / …",
    )
    before_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="变更前实体 id")
    after_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="变更后实体 id")
    sort_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="回滚时逆序用")
