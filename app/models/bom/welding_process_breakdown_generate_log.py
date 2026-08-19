"""BOM 焊接工艺拆解 — 生成批次日志模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class BomWeldingProcessBreakdownGenerateLog(AuditUserMixin, Base):
    """
    焊接工艺拆解生成批次日志

    一次「开始拆解」先写入 processing 行作为范围锁，结束后更新为终态；
    detail_text 记录完整过程。
    """

    __tablename__ = "bom_welding_process_breakdown_generate_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    calc_batch_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="拆解批次号"
    )

    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="项目/车型"
    )
    bom_version: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="材料清单版本"
    )
    customer_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="顾客名称"
    )
    snapshot_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="BOM 快照 ID"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="failed",
        comment="批次状态：processing / success / failed",
    )

    node_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="生成主表条数"
    )
    line_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="生成明细行数"
    )

    detail_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="拆解过程全文",
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="开始时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="结束时间"
    )
    operator_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="提交人用户 ID"
    )
    operator_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="提交人显示名"
    )

    __table_args__ = (
        Index("ix_wpb_gen_log_batch", "calc_batch_id"),
        Index("ix_wpb_gen_log_scope", "location", "vehicle_model", "bom_version"),
        Index("ix_wpb_gen_log_status", "status"),
        Index("ix_wpb_gen_log_started_at", "started_at"),
        Index(
            "uq_wpb_gen_processing",
            "location",
            "vehicle_model",
            "bom_version",
            unique=True,
            sqlite_where=text("status = 'processing'"),
        ),
    )
