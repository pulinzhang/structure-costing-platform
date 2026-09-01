"""冲压加工费计算批次日志模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class StampingProcessFeeCalcLog(AuditUserMixin, Base):
    """
    冲压加工费计算批次日志

    一次「开始计算」先写入 processing 行作为范围锁，结束后更新为终态；
    detail_text 记录完整过程。
    锁范围：year + location + stamping_supplier。
    """

    __tablename__ = "stamping_process_fee_calc_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    calc_batch_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="计算批次号"
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="计算年度")
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    stamping_supplier: Mapped[str] = mapped_column(String(50), nullable=False, comment="冲压工厂")
    vehicle_model: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="车型（筛选）"
    )
    version: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="版本（筛选）")

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="failed",
        comment="批次状态：processing / success / partial / failed",
    )

    total_parts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="匹配零件数"
    )
    success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="计算成功数"
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="计算失败数"
    )
    zero_fee_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="计算价为 0 数"
    )
    skipped_approved_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="跳过已审核数"
    )

    detail_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="计算过程全文",
    )

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="计算开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="计算结束时间"
    )
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="提交人用户 ID")
    operator_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="提交人显示名"
    )

    __table_args__ = (
        Index("ix_spf_calc_log_batch", "calc_batch_id"),
        Index("ix_spf_calc_log_year", "year"),
        Index("ix_spf_calc_log_location", "location"),
        Index("ix_spf_calc_log_supplier", "stamping_supplier"),
        Index("ix_spf_calc_log_status", "status"),
        Index("ix_spf_calc_log_started_at", "started_at"),
        Index(
            "uq_spf_calc_processing",
            "year",
            "location",
            "stamping_supplier",
            unique=True,
            sqlite_where=text("status = 'processing'"),
        ),
    )
