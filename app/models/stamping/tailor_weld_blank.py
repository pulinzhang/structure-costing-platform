"""
拼焊件子片表

仅存各片材料侧数据；冲压工序挂在父件 StampingPart / StampingProcess。
核价时：按子片算材料费与冲压费，再汇总到父；拼焊费在加工费列表「其它费用」录入（业务层，非本表）。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin

if TYPE_CHECKING:
    from app.models.stamping.part import StampingPart


class StampingTailorWeldBlank(AuditUserMixin, Base):
    """
    拼焊子片（材料片）

    blank_part_number 约定为父零件号 + "-N"（如 501006875AA-1）。
    本表不挂工序，避免子下再挂子。
    """

    __tablename__ = "stamping_tailor_weld_blanks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stamping_parts.id", ondelete="CASCADE"),
        nullable=False,
        comment="父件（拼焊总成）ID",
    )
    # 冗余：打开子表即可读懂归属，写入时与父件 part_number 保持一致
    parent_part_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="父件零件号（冗余，与 stamping_parts.part_number 一致）",
    )

    # 片别：序号与对外可读子件号
    blank_seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="子片序号，从 1 起（对应 -1、-2 …）",
    )
    blank_part_number: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        comment="子件零件号：父零件号-N，例：501006875AA-1",
    )

    # 材料信息（各片可不同）
    material: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="材质")
    thickness: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True, comment="料厚(mm)"
    )
    part_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True, comment="子片重量(kg)"
    )

    # 料片尺寸
    sheet_length: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="料片长/卷料宽(mm)"
    )
    sheet_width: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="料片宽/卷料步距(mm)"
    )

    # 生产信息（按本片）
    parts_per_sheet: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="可制件数：一张料单独冲本子片可出的件数",
    )
    sheet_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="料片式样")

    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    part: Mapped[StampingPart] = relationship(
        "StampingPart",
        back_populates="tailor_weld_blanks",
    )

    __table_args__ = (
        Index("ix_tailor_weld_blank_part_id", "part_id"),
        Index("ix_tailor_weld_blank_parent_part_number", "parent_part_number"),
        Index("ix_tailor_weld_blank_part_number", "blank_part_number"),
        UniqueConstraint(
            "part_id",
            "blank_seq",
            name="uix_tailor_weld_blank_part_seq",
        ),
        UniqueConstraint(
            "part_id",
            "blank_part_number",
            name="uix_tailor_weld_blank_part_number",
        ),
    )
