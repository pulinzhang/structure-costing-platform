"""工程变更上传头 — engineering_change_upload_logs。"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class EngineeringChangeUploadLog(AuditUserMixin, Base):
    """一次工程变更上传尝试（含失败）。变更单十列不落本表。"""

    __tablename__ = "engineering_change_upload_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    task_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="异步任务 ID"
    )
    upload_file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("upload_files.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
        index=True,
        comment="存档 Excel",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending / success / failed",
    )
    location: Mapped[str] = mapped_column(String(50), nullable=False, comment="采购基地")
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False, comment="项目代号")
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="顾客名称")
    effective_year: Mapped[int] = mapped_column(Integer, nullable=False, comment="生效年")
    effective_month: Mapped[int] = mapped_column(Integer, nullable=False, comment="生效月 1–12")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="源文件名")
    message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因或说明")

    process_inserted_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="工艺新增件数"
    )
    die_inserted_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="模具布点新增件数"
    )
    procurement_object_inserted_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="采购对象新增件数"
    )
    welding_breakdown_inserted_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="焊接拆解新增件数"
    )
    not_install_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="此件不装件数"
    )
    has_bom_assembly: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="材料清单是否有总成"
    )
