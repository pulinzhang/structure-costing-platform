"""BOM 焊接费计算批次日志模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class BomL0WeldingFeeCalcLog(AuditUserMixin, Base):
    """
    焊接费计算批次日志

    一次「开始计算」先写入 processing 行作为范围锁，结束后更新为终态。
    锁范围：year + location + vehicle_model + bom_version。
    """

    __tablename__ = "bom_l0_welding_fee_calc_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    calc_batch_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="计算批次号"
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="计算年度")
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="车型")
    bom_version: Mapped[str] = mapped_column(String(20), nullable=False, comment="材料清单版本")

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="failed",
        comment="批次状态：processing / success / partial / failed",
    )

    l0_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="L0 节点数")
    created_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="新增结果条数"
    )
    updated_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="更新结果条数"
    )
    skipped_approved_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="跳过已审核数"
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="计算失败数"
    )
    missing_price_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="缺单价明细合计"
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
        Index("ix_bl0wf_calc_log_batch", "calc_batch_id"),
        Index("ix_bl0wf_calc_log_year", "year"),
        Index("ix_bl0wf_calc_log_location", "location"),
        Index("ix_bl0wf_calc_log_vehicle_model", "vehicle_model"),
        Index("ix_bl0wf_calc_log_bom_version", "bom_version"),
        Index("ix_bl0wf_calc_log_status", "status"),
        Index("ix_bl0wf_calc_log_started_at", "started_at"),
        Index(
            "uq_bl0wf_calc_processing",
            "year",
            "location",
            "vehicle_model",
            "bom_version",
            unique=True,
            sqlite_where=text("status = 'processing'"),
        ),
    )
