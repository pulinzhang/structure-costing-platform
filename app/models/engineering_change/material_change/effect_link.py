"""材料变更效果链接 — engineering_change_material_effect_links。"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EngineeringChangeMaterialEffectLink(Base):
    """只为准回滚记账。effect_kind 只准 material_cutover。"""

    __tablename__ = "engineering_change_material_effect_links"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    upload_log_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "engineering_change_material_upload_logs.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
        index=True,
        comment="上传头",
    )
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "engineering_change_material_orders.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
        index=True,
        comment="切点行",
    )
    effect_kind: Mapped[str] = mapped_column(
        String(40), nullable=False, comment="只准 material_cutover"
    )
    before_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="source_part_id")
    after_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="空")
