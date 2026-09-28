"""BOM 采购对象列表 — 生成批次日志。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class BomProcurementObjectGenerateLog(AuditUserMixin, Base):
    """一次「开始生成」写入一条终态日志（同步生成，无 processing 锁）。"""

    __tablename__ = "bom_procurement_object_generate_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    calc_batch_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="生成批次号"
    )

    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目/车型")
    bom_version: Mapped[str] = mapped_column(String(20), nullable=False, comment="材料清单版本")
    snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="BOM 快照 ID")

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="failed",
        comment="批次状态：success / failed",
    )

    node_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="BOM 节点数"
    )
    object_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="采购对象条数"
    )
    other_leaf_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="其它叶子条数"
    )
    anomaly_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="异常条数"
    )
    qa_passed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="检测通过"
    )

    detail_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="生成过程全文"
    )

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="结束时间"
    )
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="提交人用户 ID")
    operator_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="提交人显示名"
    )

    __table_args__ = (
        Index("ix_po_gen_log_batch", "calc_batch_id"),
        Index("ix_po_gen_log_scope", "location", "vehicle_model", "bom_version"),
        Index("ix_po_gen_log_status", "status"),
        Index("ix_po_gen_log_started_at", "started_at"),
    )
