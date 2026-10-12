"""工程变更单表 — engineering_change_orders（列表实体 = 样表工程变更单一行）。"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class EngineeringChangeOrder(AuditUserMixin, Base):
    """变更单一行 = 一个交货总成上的一种改法（1 上传头 : N 变更单行）。"""

    __tablename__ = "engineering_change_orders"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    upload_log_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("engineering_change_upload_logs.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="上传头（整本删除/回滚用）",
    )
    upload_file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("upload_files.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="同头上存档",
    )
    before_assembly_node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bom_nodes.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="变更前交货总成 L0；RESTRICT 防删 BOM 出孤儿，禁止改 SET NULL/CASCADE",
    )
    excel_row: Mapped[int] = mapped_column(Integer, nullable=False, comment="变更单 Excel 行号")
    project_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目")
    effective_period_text: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="生效年月原文，如 2025年07月"
    )
    change_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="变更类型五句之一")
    before_assembly_part_number: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="变更前总成"
    )
    after_assembly_part_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="变更后总成；完成停止空"
    )
    assembly_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="总成名称"
    )
    part_level: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="零件层级：总成 / 一级 / 二级"
    )
    before_part_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="变更前零件"
    )
    after_part_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="变更后零件"
    )
    part_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="零件名称")
    seq_no: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="材料清单序号（系统带出）"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="active / rolled_back",
    )
